import collections
import multiprocessing

import json
import torch
from numpy.random import RandomState
from torch.utils.data import Dataset


class DatasetSpec:
    SHAPE_NAME = 100
    INPUT_PC = 200
    TARGET_NORMAL = 300
    GT_DENSE_PC = 400
    GT_DENSE_NORMAL = 500


def deterministic_hash(data):
    """
    :param data: Any type
    :return: a deterministic hash value of integer type (32bit)
    """
    import zlib
    jval = json.dumps(data, ensure_ascii=False, sort_keys=True,
                      indent=None, separators=(',', ':'))
    return zlib.adler32(jval.encode('utf-8'))


class RandomSafeDataset(Dataset):
    """
    A dataset class that provides a deterministic random seed.
    However, in order to have consistent validation set, we need to set is_val=True for validation/test sets.
    Usage: First, inherent this class.
           Then, at the beginning of your get_item call, get an rng;
           Last, use this rng as the random state for your program.
    """

    def __init__(self, seed: int, _is_val: bool = False, skip_on_error: bool = False):
        self._seed = seed
        self._is_val = _is_val
        self.skip_on_error = skip_on_error
        if not self._is_val:
            self._manager = multiprocessing.Manager()
            self._read_count = self._manager.dict()

    def get_rng(self, idx):
        if self._is_val:
            return RandomState(self._seed)
        if idx not in self._read_count:
            self._read_count[idx] = 0
        rng = RandomState(deterministic_hash((idx, self._read_count[idx], self._seed)))
        self._read_count[idx] += 1
        return rng

    def _get_item(self, data_id, rng):
        raise NotImplementedError

    def __getitem__(self, data_id):
        rng = self.get_rng(data_id)
        if self.skip_on_error:
            try:
                return self._get_item(data_id, rng)
            except ConnectionAbortedError:
                return self.__getitem__(rng.randint(0, len(self) - 1))
            except Exception:
                # Just return a random other item.
                print(f"Warning: Get item {data_id} error, but handled.")
                return self.__getitem__(rng.randint(0, len(self) - 1))
        else:
            try:
                return self._get_item(data_id, rng)
            except ConnectionAbortedError:
                return self.__getitem__(rng.randint(0, len(self) - 1))


def list_collate(batch):
    """
    This just do not stack batch dimension.
    """
    elem = None
    for e in batch:
        if e is not None:
            elem = e
            break
    elem_type = type(elem)
    if isinstance(elem, torch.Tensor):
        return batch
    elif elem_type.__module__ == 'numpy' and elem_type.__name__ != 'str_' \
            and elem_type.__name__ != 'string_':
        if elem_type.__name__ == 'ndarray' or elem_type.__name__ == 'memmap':
            return list_collate([torch.as_tensor(b) if b is not None else None for b in batch])
        elif elem.shape == ():  # scalars
            return torch.as_tensor(batch)
    elif isinstance(elem, float):
        return torch.tensor(batch, dtype=torch.float64)
    elif isinstance(elem, int):
        return torch.tensor(batch)
    elif isinstance(elem, str):
        return batch
    elif isinstance(elem, collections.abc.Mapping):
        return {key: list_collate([d[key] for d in batch]) for key in elem}
    elif isinstance(elem, collections.abc.Sequence):
        # check to make sure that the elements in batch have consistent size
        it = iter(batch)
        elem_size = len(next(it))
        if not all(len(elem) == elem_size for elem in it):
            raise RuntimeError('each element in list of batch should be of equal size')
        transposed = zip(*batch)
        return [list_collate(samples) for samples in transposed]

    return batch
