#!/usr/bin/env python3

from typing import Optional, Literal, List, Union

import numpy as np
import tqdm
import npimage
import npimage.graphics

from . import lookup, template_spaces, transforms


def make_colormip(neuron: Union[int, List[int], str],
                  target_space: str = 'brain',
                  level_of_detail: Literal['faces', 'vertices', 'skeleton'] = 'vertices',
                  composite: bool = False,
                  save: bool = False,
                  save_path: Optional[str] = None,
                  verbose: bool = False) -> Optional[np.ndarray]:
    """
    Create a color MIP (depth-colored maximum intensity projection) image of a neuron.

    https://www.janelia.org/open-science/color-depth-mip
    This implementation of the ColorMIP algorithm was written by Stephan
    Gerhard (braincircuits.io) based on Otsuna et al. 2018 bioRxiv.
    https://www.biorxiv.org/content/10.1101/318006
    The output of this algorithm is nearly identical to the image produced
    by the original and more widely used ColorMIP Fiji plugin. Small differences
    of 1-2% in the RBG values are present, but are not really noticeable by eye,
    and seem unlikely to cause issues in ColorMIP searches.

    Parameters
    ----------
    neuron : int or list of ints or str
        The segment ID(s) from the BANC segmentation to make colormips of,
        or a cell type to look up seg_id(s) for using fanc.lookup.

    target_space: str, default 'brain'
        Which space to render the color MIP in.
        Set this to 'brain' to use the most common brain space
          for Janelia's colormips, JRC2018_UNISEX_20x_HR.
        Set this to 'VNC' to use the most common VNC space for
          Janelia's colormips, JRC2018_VNC_UNISEX_461.
        See banc.template_spaces.template_info for a full list of
          template spaces that can be provided for this argument.

    level_of_detail: 'vertices' (default), 'faces', or 'skeleton'
        See docstring for render_neuron_into_template_space for details.

    composite: bool, default False
        If True, create a composite colormip by combining the colormips
        of multiple seg_ids into a single image. If False, create a separate
        colormip for each seg_id.

    save: bool, default False
        If True, save the colormip to a file.
        If False, return the colormip as a numpy array.

    save_path: str or list of str, default None
        If save=True, this should be a string (for a single seg_id) or list
        of strings (for a list of seg_ids) with the path(s) to save the
        colormip(s) to. If None, the default save path will be
        {seg_id}_in_{target_space}.png.

    verbose: bool, default False
        If True, print additional information about the rendering process.
    """
    if target_space.lower() == 'brain':
        target_space = 'JRC2018_UNISEX_20x_HR'
    elif target_space.lower() == 'vnc':
        target_space = 'JRC2018_VNC_UNISEX_461'

    if isinstance(neuron, str):
        seg_id = lookup.cells_annotated_with(neuron)
        if verbose:
            print(f'Found {len(seg_id)} seg_id(s) for query "{neuron}": {seg_id}')
        if composite and save and save_path is None:
            neuron = neuron.replace(' ', '-')
            segids_str = ','.join(map(str, seg_id))
            save_path = f'{neuron}_{segids_str}_in_{target_space}.png'
    else:
        seg_id = neuron

    try:
        if composite:
            # This just skips the block below that makes one image per seg_id
            # and proceeds to the block that renders all seg_ids in one image.
            raise TypeError
        iter(seg_id)
        if isinstance(save_path, str):
            raise ValueError('Cannot specify a single save_path when rendering'
                             ' multiple neurons. Provide a list of save_paths instead.')
        elif isinstance(save_path, (list, tuple)) and len(save_path) == len(seg_id):
            colormips = [make_colormip(seg, target_space,
                                       level_of_detail=level_of_detail,
                                       save=save, save_path=path,
                                       verbose=verbose)
                         for seg, path in zip(seg_id, save_path)]
        elif save_path is not None:
            raise ValueError('If save_path is provided, it must be a list'
                             ' with the same length as seg_id')
        else:
            colormips = [make_colormip(seg, target_space,
                                       level_of_detail=level_of_detail,
                                       save=save, save_path=None,
                                       verbose=verbose)
                         for seg in seg_id]
        if not save:
            return colormips
        return
    except TypeError:
        pass

    from skimage.color import rgb2hsv, hsv2rgb
    rendered_image = render_neuron_into_template_space(
        seg_id=seg_id,
        target_space=target_space,
        level_of_detail=level_of_detail,
        save=False,
        verbose=verbose
    )
    target_info = template_spaces.get_template_info(target_space)

    # This implementation of the ColorMIP algorithm was written by Stephan
    # Gerhard (braincircuits.io) based on Otsuna et al. 2018 bioRxiv.
    # The output of this algorithm is nearly identical to the image produced
    # by the original and more widely used ColorMIP Fiji plugin. Small differences
    # of 1-2% in the RBG values are present, but are not really noticeable by eye,
    # and seem unlikely to cause issues in ColorMIP searches.
    target_zmax = target_info['stack dimensions'][-1] - 1
    image_zmaxes = np.argmax(rendered_image, axis=2).astype(np.float64)
    image_zmaxes = (image_zmaxes / target_zmax * 255).astype(np.uint32)
    colormip = np.zeros((rendered_image.shape[0], rendered_image.shape[1], 3),
                        dtype=np.uint8)
    for i in range(image_zmaxes.shape[0]):
        for j in range(image_zmaxes.shape[1]):
            if image_zmaxes[i, j] != 0:
                hsv = rgb2hsv(np.array(depth_lut[image_zmaxes[i, j]], dtype=np.double))
                hsv[2] = 255
                colormip[i, j, :] = hsv2rgb(hsv).astype(np.uint8)

    colormip = colormip.transpose(1, 0, 2).astype(np.uint8)  # Flip xyc to yxc
    if target_space == 'JRC2018_VNC_UNISEX_461':
        # Add the 90 pixel header that all Janelia VNC colormips have
        colormip = np.vstack([np.zeros((90, 573, 3), dtype=np.uint8), colormip]).astype(np.uint8)
    if not save:
        return colormip
    if not isinstance(seg_id, str):
        try:
            seg_id = ','.join(map(str, seg_id))
        except TypeError:
            pass
    if save_path is None:
        save_path = f'{seg_id}_in_{target_space}.png'
    npimage.save(colormip, save_path)
    if verbose:
        print('Saved colormip to:', save_path)


def render_neuron_into_template_space(seg_id: Union[int, List[int]],
                                      target_space: str,
                                      level_of_detail: Literal['faces', 'vertices', 'skeleton'] = 'vertices',
                                      save: bool = False,
                                      save_path: Optional[str] = None,
                                      compress: bool = True,
                                      verbose: bool = False) -> Optional[np.ndarray]:
    """
    Create an image volume in .nrrd format containing a rendering of a
    neuron from the BANC aligned to some template space, with the image
    volume's dimensions and voxel size matching the template space.

    Parameters
    ----------
    seg_id : int
        The segment ID(s) from the BANC segmentation to render.
        If multiple seg_ids are provided, they will be overlaid in the rendering.

    target_space: str
       See banc.template_spaces.template_info for a list of template spaces that can be
       provided for this argument.

    level_of_detail: 'vertices' (default), 'faces', or 'skeleton'
        If 'faces', 'every triangle in the mesh will be rendered as a filled
        triangle. This is the slowest but most accurate rendering.
        If 'vertices', every vertex in the mesh will be rendered as a point. This
        is nearly as accurate as 'faces' but much faster, so it's the default.
        If 'skeleton', the skeletonized version of the neuron will be rendered.
        Presumably faster, but lowest level of accuracy. Not yet implemented.

    compress: bool (default True)
        If True, save the .nrrd with gzip encoding. If False, save with raw
        encoding. (Because the image volume created here is all black except for
        a small percent of the pixels that are white to represent the neuron,
        compression gives file sizes <1MB where raw gives file sizes >100MB.)
    """
    if level_of_detail == 'skeleton':
        raise NotImplementedError('Skeleton rendering is not yet implemented')

    # Render into a target-space-sized numpy array
    target_info = template_spaces.get_template_info(target_space)
    rendered_image = np.zeros(target_info['stack dimensions'], dtype=np.uint8)

    if isinstance(seg_id, str):
        seg_ids = [int(seg_id)]
    elif np.issubdtype(type(seg_id), np.integer):
        seg_ids = [seg_id]
    else:
        seg_ids = seg_id

    for seg_id in seg_ids:
        my_mesh = transforms.template_alignment.align_mesh(
            seg_id, target_space, verbose=verbose
        )

        # Convert from microns to pixels in the target space
        my_mesh.vertices = my_mesh.vertices / target_info['voxel size']

        if verbose:
            print(f'Rendering mesh {level_of_detail} into {target_space} space')
        if level_of_detail == 'faces':
            for face in tqdm.tqdm(my_mesh.faces):
                npimage.graphics.drawtriangle(
                    rendered_image,
                    my_mesh.vertices[face[0]],
                    my_mesh.vertices[face[1]],
                    my_mesh.vertices[face[2]],
                    255,
                    fill_value=255,
                    watertight=False
                )
        elif level_of_detail == 'vertices':
            npimage.graphics.drawpoint(rendered_image, my_mesh.vertices, 255)

    if not save:
        return rendered_image
    if save_path is None:
        save_path = 'segid{}_in_{}.nrrd'.format(seg_id, target_space)
    npimage.save(rendered_image,
                 save_path,
                 metadata=template_spaces.get_nrrd_metadata(target_space),
                 compress=compress,
                 dim_order='xyz')


# The lookup table used by the Janelia ColorMIP algorithm to map depth
# values to RGB colors. First convert the depth values to the range
# 0-255, then ask for depth_lut[depth] to get the RGB color for that pixel.
depth_lut = [
    [127,0,255],[125,3,255],[124,6,255],[122,9,255],[121,12,255],[120,15,255],
    [119,18,255],[118,21,255],[116,24,255],[115,27,255],[114,30,255],[113,33,255],
    [112,36,255],[110,39,255],[109,42,255],[108,45,255],[106,48,255],[105,51,255],
    [104,54,255],[103,57,255],[101,60,255],[100,63,255],[99,66,255],[98,69,255],
    [96,72,255],[95,75,255],[94,78,255],[93,81,255],[92,84,255],[90,87,255],[89,90,255],
    [87,93,255],[86,96,255],[84,99,255],[83,102,255],[81,105,255],[80,108,255],
    [78,111,255],[77,114,255],[75,117,255],[74,120,255],[72,123,255],[71,126,255],
    [69,129,255],[68,132,255],[66,135,255],[65,138,255],[63,141,255],[62,144,255],
    [60,147,255],[59,150,255],[57,153,255],[56,156,255],[54,159,255],[53,162,255],
    [51,165,255],[50,168,255],[48,171,255],[47,174,255],[45,177,255],[44,180,255],
    [42,183,255],[41,186,255],[39,189,255],[38,192,255],[36,195,255],[35,198,255],
    [33,201,255],[32,204,255],[30,207,255],[29,210,255],[27,213,255],[26,216,255],
    [24,219,255],[23,222,255],[21,225,255],[20,228,255],[18,231,255],[16,234,255],
    [14,237,255],[12,240,255],[9,243,255],[6,246,255],[3,249,255],[1,252,255],
    [0,254,255],[3,255,252],[6,255,249],[9,255,246],[12,255,243],[15,255,240],
    [18,255,237],[21,255,234],[24,255,231],[27,255,228],[30,255,225],[33,255,222],
    [36,255,219],[39,255,216],[42,255,213],[45,255,210],[48,255,207],[51,255,204],
    [54,255,201],[57,255,198],[60,255,195],[63,255,192],[66,255,189],[69,255,186],
    [72,255,183],[75,255,180],[78,255,177],[81,255,174],[84,255,171],[87,255,168],
    [90,255,165],[93,255,162],[96,255,159],[99,255,156],[102,255,153],[105,255,150],
    [108,255,147],[111,255,144],[114,255,141],[117,255,138],[120,255,135],[123,255,132],
    [126,255,129],[129,255,126],[132,255,123],[135,255,120],[138,255,117],[141,255,114],
    [144,255,111],[147,255,108],[150,255,105],[153,255,102],[156,255,99],[159,255,96],
    [162,255,93],[165,255,90],[168,255,87],[171,255,84],[174,255,81],[177,255,78],
    [180,255,75],[183,255,72],[186,255,69],[189,255,66],[192,255,63],[195,255,60],
    [198,255,57],[201,255,54],[204,255,51],[207,255,48],[210,255,45],[213,255,42],
    [216,255,39],[219,255,36],[222,255,33],[225,255,30],[228,255,27],[231,255,24],
    [234,255,21],[237,255,18],[240,255,15],[243,255,12],[246,255,9],[249,255,6],
    [252,255,3],[254,255,0],[255,252,3],[255,249,6],[255,246,9],[255,243,12],
    [255,240,15],[255,237,18],[255,234,21],[255,231,24],[255,228,27],[255,225,30],
    [255,222,33],[255,219,36],[255,216,39],[255,213,42],[255,210,45],[255,207,48],
    [255,204,51],[255,201,54],[255,198,57],[255,195,60],[255,192,63],[255,189,66],
    [255,186,69],[255,183,72],[255,180,75],[255,177,78],[255,174,81],[255,171,84],
    [255,168,87],[255,165,90],[255,162,93],[255,159,96],[255,156,99],[255,153,102],
    [255,150,105],[255,147,108],[255,144,111],[255,141,114],[255,138,117],[255,135,120],
    [255,132,123],[255,129,126],[255,126,129],[255,123,132],[255,120,135],[255,117,138],
    [255,114,141],[255,111,144],[255,108,147],[255,105,150],[255,102,153],[255,99,156],
    [255,96,159],[255,93,162],[255,90,165],[255,87,168],[255,84,171],[255,81,173],
    [255,78,174],[255,75,175],[255,72,176],[255,69,177],[255,66,178],[255,63,179],
    [255,60,180],[255,57,181],[255,54,182],[255,51,183],[255,48,184],[255,45,185],
    [255,42,186],[255,39,187],[255,36,188],[255,33,189],[255,30,190],[255,27,191],
    [255,24,192],[255,21,193],[255,18,194],[255,15,195],[255,12,196],[255,9,197],
    [255,6,198],[255,3,199],[255,0,200]
]
