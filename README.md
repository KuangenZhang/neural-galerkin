# A Neural Galerkin Solver for Accurate Surface Reconstruction

### [**Paper**](https://dl.acm.org/doi/abs/10.1145/3550454.3555457) | [**Video**](https://youtu.be/QT5k0ZxDFfo) | [**Talk**](https://youtu.be/dYy-lzeMsCQ)

![](./assets/teaser.jpg)

This repository contains the implementation of the above paper. It is accepted to **ACM SIGGRAPH Asia 2022**.
- Authors: [Jiahui Huang](https://cg.cs.tsinghua.edu.cn/people/~huangjh/), [Hao-Xiang Chen](), [Shi-Min Hu](https://cg.cs.tsinghua.edu.cn/shimin.htm)
    - Contact Jiahui either via email or github issues.


If you find our code or paper useful, please consider citing:
```bibtex
@article{huang2022neuralgalerkin,
  author = {Huang, Jiahui and Chen, Hao-Xiang and Hu, Shi-Min},
  title = {A Neural Galerkin Solver for Accurate Surface Reconstruction},
  year = {2022},
  publisher = {Association for Computing Machinery},
  address = {New York, NY, USA},
  volume = {41},
  number = {6},
  doi = {10.1145/3550454.3555457},
  journal = {ACM Trans. Graph.},
}
```

## Introduction

This repository is divided into two parts:
- `pytorch_spsr`: A GPU-accelerated differentiable implementation of Screened Poisson Surface Reconstruction (SPSR) using PyTorch.
- `neural_galerkin`: The learning part in the paper that is dependent on `pytorch_spsr`, including the adaptive CNN, data loader and the full training/evaluation scripts.

## Getting started

🌱 If you just want to use `pytorch_spsr`, then simply install it like a standard Python package, because the module is compatible with `setuptools`:
```shell
cd neural-galerkin/
conda create -n spsr python=3.10
conda activate spsr
sh install.sh
```
## An example of using `torch-spsr`
```shell
cd examples
python main.py
```

## Using `torch-spsr`

After installing `torch-spsr` package, you may use it in either of the following two ways:

1. Using the wrapper function to obtain the triangle mesh directly:

```python
import torch_spsr

v, f = torch_spsr.reconstruct(
  pts,          # torch.Tensor (N, 3)
  pts_normal,   # torch.Tensor (N, 3)
  depth=4, 
  voxel_size=0.002
)
# v: triangle vertices (V, 3)
# f: triangle indices (T, 3)
```

The resulting triangle mesh representation can be visualized using:
```python
from pycg import vis
vis.show_3d([vis.mesh(v, f)])
```

- The above commands are exemplified with `python examples/main.py`:
![](./assets/horse.gif)

2. Using the `Reconstructor` class to obtain a differentiable implicit function:

```python
from torch_spsr.core.hashtree import HashTree
from torch_spsr.core.reconstructor import Reconstructor
from torch_spsr.bases.bezier_tensor import BezierTensorBasis

hash_tree = HashTree(pts, voxel_size=0.002, depth=4)
hash_tree.build_encoder_hierarchy_adaptive(min_density=32.0)
hash_tree.reflect_decoder_coords()

# Splat point normals onto the tree
normal_data = {}
sample_weight = 1.0 / hash_tree.xyz_density
for d in range(hash_tree.depth):
    depth_mask = hash_tree.xyz_depth == d
    normal_data_depth = hash_tree.splat_data(
        pts[depth_mask], hash_tree.DECODER, d, 
        pts_normal[depth_mask] * sample_weight[depth_mask, None]
    )
    normal_data[d] = normal_data_depth / (hash_tree.get_stride(hash_tree.DECODER, d) ** 3)

# Perform reconstruction
reconstructor = Reconstructor(hash_tree, BezierTensorBasis())
reconstructor.sample_weight = sample_weight
reconstructor.solve_multigrid(
    hash_tree.depth - 1, 0, normal_data,
    screen_alpha=4.0, screen_xyz=pts, solver="pcg"
)

# Evaluate the implicit function: suppose query_pos is torch.Tensor (M, 3)
f_val = reconstructor.evaluate_chi(query_pos)   # -> (M,)
```

## Reproducing our results 

Please follow the commands below to run all of our experiments.
As we adopted a 2-stage training strategy, you may have to specify `--load_pretrained` when running the 2nd stage to indicate where the trained model for the 1st stage lies in.

### ShapeNet

Please download the dataset from [here](https://s3.eu-central-1.amazonaws.com/avg-projects/occupancy_networks/data/dataset_small_v1.1.zip), and put the extracted `onet` folder under `data/shapenet`.

- 1K input, No noise (trained model download [here](https://drive.google.com/file/d/1WMYrhTtvTCWRVbMZiVfxmB3fvvNASUwe/view?usp=sharing))
```shell
# Test our trained model (add -v to visualize)
python test.py none --ckpt checkpoints/shapenet-perfect1k/main/paper/checkpoints/best.ckpt 
# Train yourself: phase1
python train.py configs/shapenet/full_1k_perfect_p1.yaml
# Train yourself: phase2
python train.py configs/shapenet/full_1k_perfect.yaml
```

- 3K input, Small noise (trained model download [here](https://drive.google.com/file/d/1aE7XAnl8ffdbU22F6ZZkhiU9-zoNGAt-/view?usp=sharing))
```shell
# Test our trained model (add -v to visualize)
python test.py none --ckpt checkpoints/shapenet-noise3k/main/paper/checkpoints/best.ckpt 
# Train yourself: phase1
python train.py configs/shapenet/full_3k_noise_p1.yaml 
# Train yourself: phase2
python train.py configs/shapenet/full_3k_noise.yaml 
```

- 3K input, Large noise (trained model download [here](https://drive.google.com/file/d/13CGwy3k4Mny6__zbDHrFiiZaUkv1CelT/view?usp=sharing))
```shell
# Test our trained model (add -v to visualize)
python test.py none --ckpt checkpoints/shapenet-noiser3k/main/paper/checkpoints/best.ckpt 
# Train yourself: phase1
python train.py configs/shapenet/full_3k_noiser_p1.yaml 
# Train yourself: phase2
python train.py configs/shapenet/full_3k_noiser.yaml 
```

### Matterport3D

Please download the dataset from [here](https://drive.google.com/file/d/18c02XjpWHtP7vjFhQyuokH90G8ikxo23/view?usp=sharing), and put the extracted `matterport` folder under `data/`.

- Without Normal (trained model download [here](https://drive.google.com/file/d/1ouek3Ywt8QVf-9D55KhF_C_15SSvRg8Y/view?usp=sharing))
```shell
# Test our trained model (add -v to visualize)
python test.py none --ckpt checkpoints/matterport/without_normal/paper/checkpoints/best.ckpt 
# Train yourself: phase1
python train.py configs/matterport/full_wonormal_p1.yaml 
# Train yourself: phase2
python train.py configs/matterport/full_wonormal.yaml 
```

- With Normal (trained model download [here](https://drive.google.com/file/d/1ouek3Ywt8QVf-9D55KhF_C_15SSvRg8Y/view?usp=sharing))
```shell
# Test our trained model (add -v to visualize)
python test.py none --ckpt checkpoints/matterport/with_normal/paper/checkpoints/best.ckpt 
# Train yourself: phase1
python train.py configs/matterport/full_wnormal_p1.yaml 
# Train yourself: phase2
python train.py configs/matterport/full_wnormal.yaml 
```

### D-FAUST

Please download the dataset from [here](https://drive.google.com/file/d/1ghL6RRQjZAEj4jCfozW11pDWypPnpp7m/view?usp=sharing), and put the extracted `dfaust` folder under `data/`.

- Origin split (trained models download [here](https://drive.google.com/file/d/1zjpMhymlAbYQv2jplYw4eWfkywVzpoKd/view?usp=sharing))
```shell
# Test our trained model (add -v to visualize)
python test.py none --ckpt checkpoints/dfaust/origin/paper/checkpoints/best.ckpt 
# Train yourself: phase1
python train.py configs/dfaust/full_10k_p1.yaml
# Train yourself: phase2
python train.py configs/dfaust/full_10k.yaml
```

- Novel split (test only)
```shell
# Test our trained model (add -v to visualize)
python test.py configs/dfaust/data_10k_novel.yaml --ckpt checkpoints/dfaust/origin/paper/checkpoints/best.ckpt -v
```

## Acknowledgements

We thank anonymous reviewers for their constructive feedback. 
This work was supported by the National Key R&D Program of China (No. 2021ZD0112902), Research Grant of Beijing Higher Institution Engineering Research Center and Tsinghua-Tencent Joint Laboratory for Internet Innovation Technology.

Part of the code is directly borrowed from [torchsparse](https://github.com/mit-han-lab/torchsparse) and [Convolutional Occupancy Networks](https://github.com/autonomousvision/convolutional_occupancy_networks).
