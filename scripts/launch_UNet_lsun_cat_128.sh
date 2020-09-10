#!/bin/bash

## User python environment
HOME2=/disk_c/$(whoami)
PYTHON_VIRTUAL_ENVIRONMENT=wtvae
CONDA_ROOT=$HOME2/ananconda3

## Activate WMLCE virtual environment 
source ${CONDA_ROOT}/etc/profile.d/conda.sh
conda activate $PYTHON_VIRTUAL_ENVIRONMENT

## Setting GPU
export CUDA_VISIBLE_DEVICES=0

echo " Running on GPU devices $CUDA_VISIBLE_DEVICES"
echo ""
echo " Run started at:- "
date

python src/train_unet_128.py \
--dataset lsun-cat \
--train_dir $HOME2/data/lsun/ --valid_dir $HOME2/data/lsun/ \
--batch_size 128 --image_size 256 --mask_dim 64 --lr 1e-4 \
--num_epochs 100 --output_dir $HOME2/not-so-biggan-decoder/results/unet_lsun_cat_128/ \
--project_name unet_lsun_cat_128 \
--save_every 2000 --valid_every 2000 --log_every 100 \
# --resume --checkpoint 197000 \
