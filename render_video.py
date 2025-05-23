#
# Copyright (C) 2023, Inria
# GRAPHDECO research group, https://team.inria.fr/graphdeco
# All rights reserved.
#
# This software is free for non-commercial, research and evaluation use 
# under the terms of the LICENSE.md file.
#
# For inquiries contact  george.drettakis@inria.fr
#

import torch
from torch.utils.data import DataLoader
from scene import Scene
import os
from tqdm import tqdm
from os import makedirs
from gaussian_renderer import render
import torchvision
from utils.general_utils import safe_state
from argparse import ArgumentParser
from arguments import ModelParams, PipelineParams, get_combined_args
from gaussian_renderer import GaussianModel
from scene import GaussianModelTypes
import imageio
import numpy as np

def render_sets(args,dataset : ModelParams, iteration : int, pipeline : PipelineParams, skip_train : bool, skip_test : bool):
    with torch.no_grad():
        dataset.timestamp=args.timestamp
        dataset.model_version=args.model_version
        Model=GaussianModelTypes[args.model_version]
        if args.model_version=="SeperateRepreIsotropicGaussianModel":
            gaussians =Model(dataset.sh_degree, dataset.approx_l,dataset.approx_l_global)
        else:
            gaussians =Model(dataset.sh_degree, dataset.approx_l)
        scene = Scene(dataset, gaussians, load_iteration=iteration, shuffle=False)

        bg_color = [1,1,1] if dataset.white_background else [0, 0, 0]
        background = torch.tensor(bg_color, dtype=torch.float32, device="cuda")

        model_path = dataset.model_path
        iteration = scene.loaded_iter

        render_path = os.path.join(model_path,args.timestamp, "path.mp4")

        views = scene.getVisCameras()
        rendering_list = []
        for idx, view in enumerate(tqdm(views, desc="Rendering progress")):
            if type(view) is list:
                view = view[0]
            rendering = render(view, gaussians, pipeline, background)["render"]
            rendering_list.append((255*np.clip(rendering.cpu().numpy(),0,1)).astype(np.uint8).transpose(1, 2, 0))

        print(rendering_list[0].shape)
        imageio.mimwrite(render_path, rendering_list)

if __name__ == "__main__":
    # Set up command line argument parser
    parser = ArgumentParser(description="Testing script parameters")
    model = ModelParams(parser, sentinel=True)
    pipeline = PipelineParams(parser)
    parser.add_argument("--iteration", default=-1, type=int)
    parser.add_argument("--skip_train", action="store_true")
    parser.add_argument("--skip_test", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--timestamp", type=str)
    args = get_combined_args(parser)
    print("Rendering " + args.model_path)

    # Initialize system state (RNG)
    safe_state(args.quiet)

    render_sets(args,model.extract(args), args.iteration, pipeline.extract(args), args.skip_train, args.skip_test)
