"""Exercise the weapon-only coverage pass with a real shared D24 multisample attachment."""
from pathlib import Path
import sys

import numpy as np
from OpenGL import EGL, GL
from OpenGL.GL.shaders import compileProgram, compileShader

width, height = 48, 36
display = EGL.eglGetDisplay(EGL.EGL_DEFAULT_DISPLAY)
major, minor, count = EGL.EGLint(), EGL.EGLint(), EGL.EGLint()
assert EGL.eglInitialize(display, major, minor)
assert EGL.eglBindAPI(EGL.EGL_OPENGL_API)
attributes = (EGL.EGLint * 9)(
    EGL.EGL_SURFACE_TYPE, EGL.EGL_PBUFFER_BIT, EGL.EGL_RENDERABLE_TYPE, EGL.EGL_OPENGL_BIT,
    EGL.EGL_RED_SIZE, 8, EGL.EGL_GREEN_SIZE, 8, EGL.EGL_NONE,
)
configs = (EGL.EGLConfig * 1)()
assert EGL.eglChooseConfig(display, attributes, configs, 1, count) and count.value
surface_attributes = (EGL.EGLint * 5)(EGL.EGL_WIDTH, width, EGL.EGL_HEIGHT, height, EGL.EGL_NONE)
surface = EGL.eglCreatePbufferSurface(display, configs[0], surface_attributes)
context = EGL.eglCreateContext(display, configs[0], EGL.EGL_NO_CONTEXT, None)
assert EGL.eglMakeCurrent(display, surface, surface, context)

target = GL.GL_FRAMEBUFFER
attachment = GL.GL_COLOR_ATTACHMENT0
rb_target = GL.GL_RENDERBUFFER
depth = GL.glGenRenderbuffers(1)
GL.glBindRenderbuffer(rb_target, depth)
GL.glRenderbufferStorageMultisample(rb_target, 4, GL.GL_DEPTH_COMPONENT24, width, height)


def framebuffer(internal, samples=False):
    fbo = GL.glGenFramebuffers(1)
    GL.glBindFramebuffer(target, fbo)
    if samples:
        color = GL.glGenRenderbuffers(1)
        GL.glBindRenderbuffer(rb_target, color)
        GL.glRenderbufferStorageMultisample(rb_target, 4, internal, width, height)
        GL.glFramebufferRenderbuffer(target, attachment, rb_target, color)
        GL.glFramebufferRenderbuffer(target, GL.GL_DEPTH_ATTACHMENT, rb_target, depth)
    else:
        color = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, color)
        fmt = GL.GL_RED if internal == GL.GL_R8 else GL.GL_RGBA
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, internal, width, height, 0, fmt, GL.GL_UNSIGNED_BYTE, None)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
        GL.glFramebufferTexture2D(target, attachment, GL.GL_TEXTURE_2D, color, 0)
    assert GL.glCheckFramebufferStatus(target) == GL.GL_FRAMEBUFFER_COMPLETE
    return fbo, color


def link(vertex, frag):
    return compileProgram(compileShader(vertex, GL.GL_VERTEX_SHADER),
                          compileShader(frag, GL.GL_FRAGMENT_SHADER), validate=False)


def draw(shader, positions):
    location = GL.glGetAttribLocation(shader, 'attr_Position')
    GL.glEnableVertexAttribArray(location)
    GL.glVertexAttribPointer(location, positions.shape[1], GL.GL_FLOAT, False, 0, positions)
    GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, len(positions))
    GL.glDisableVertexAttribArray(location)


def resolve(source, dest):
    GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, source)
    GL.glBindFramebuffer(GL.GL_DRAW_FRAMEBUFFER, dest)
    GL.glBlitFramebuffer(0, 0, width, height, 0, 0, width, height, GL.GL_COLOR_BUFFER_BIT, GL.GL_NEAREST)


def read(fbo, fmt=GL.GL_RGBA, channels=4):
    GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, fbo)
    data = GL.glReadPixels(0, 0, width, height, fmt, GL.GL_FLOAT)
    return np.frombuffer(data, dtype='f4').copy().reshape(height, width, channels)


scene, _ = framebuffer(GL.GL_RGBA16F, samples=True)
weapon_mask, _ = framebuffer(GL.GL_R8, samples=True)
scratch, scene_texture = framebuffer(GL.GL_RGBA16F)
output, _ = framebuffer(GL.GL_RGBA16F)
coverage_fbo, coverage_texture = framebuffer(GL.GL_R8)
flat_vert = '#version 150\nin vec3 attr_Position;void main(){gl_Position=vec4(attr_Position, 1.0);}'
flat = link(flat_vert, '#version 150\nuniform vec4 paint;out vec4 pixel;void main(){pixel=paint;}')
actual = (Path(sys.argv[1]) / 'SP/code/rend2/glsl/viewmodeledge_fp.glsl').read_text()
filter_program = link(flat_vert, '#version 150\nout vec4 pixel;\n#define gl_FragColor pixel\n' + actual)
quad = np.array([[-1, -1, 0], [1, -1, 0], [-1, 1, 0], [1, 1, 0]], dtype='f4')
paint = GL.glGetUniformLocation(flat, 'paint')


def frame(slope, phase, blocker=False):
    GL.glViewport(0, 0, width, height)
    GL.glBindFramebuffer(target, scene)
    GL.glDepthMask(True)
    GL.glEnable(GL.GL_DEPTH_TEST)
    GL.glDepthFunc(GL.GL_LESS)
    GL.glClearColor(0.8, 0.8, 0.8, 0.7)
    GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
    GL.glUseProgram(flat)
    x_lo = 2 * (width / 2 + phase) / width - 1
    x_hi = 2 * (width / 2 + phase + slope * height) / width - 1
    positions = np.array([[-1, -1, -0.5], [x_lo, -1, -0.5],
                          [-1, 1, -0.5], [x_hi, 1, -0.5]], dtype='f4')
    GL.glUniform4f(paint, 0.10, 0.10, 0.10, 0.7)
    draw(flat, positions)
    if blocker:
        covers = quad.copy()
        covers[:, 2] = -0.75
        GL.glEnable(GL.GL_SCISSOR_TEST)
        GL.glScissor(0, 10, width, 3)
        GL.glUniform4f(paint, 1.0, 0.1, 0.1, 0.7)
        draw(flat, covers)
        GL.glDisable(GL.GL_SCISSOR_TEST)
    resolve(scene, scratch)
    resolve(scene, output)

    GL.glBindFramebuffer(target, weapon_mask)
    GL.glClearBufferfv(GL.GL_COLOR, 0, [1, 1, 1, 1])
    GL.glDepthMask(False)
    GL.glDepthFunc(GL.GL_EQUAL)
    GL.glEnable(GL.GL_BLEND)
    GL.glBlendFunc(GL.GL_ZERO, GL.GL_ZERO)
    draw(flat, positions)
    GL.glDisable(GL.GL_BLEND)
    GL.glDisable(GL.GL_DEPTH_TEST)
    resolve(weapon_mask, coverage_fbo)

    GL.glBindFramebuffer(target, output)
    GL.glUseProgram(filter_program)
    for unit, name, texture in [(0, 'u_TextureMap', scene_texture), (1, 'u_ScreenDepthMap', coverage_texture)]:
        GL.glActiveTexture(GL.GL_TEXTURE0 + unit)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
        GL.glUniform1i(GL.glGetUniformLocation(filter_program, name), unit)
    GL.glUniform4f(GL.glGetUniformLocation(filter_program, 'u_ViewInfo'), 0, 0, width - 1, height - 1)
    draw(filter_program, quad)
    assert GL.glGetError() == GL.GL_NO_ERROR
    original = read(scratch)
    final = read(output)
    c = 1.0 - read(coverage_fbo, GL.GL_RED, 1)[..., 0]
    mask = (c > 0.001) & (c < 0.999)
    assert np.array_equal(original[~mask], final[~mask])
    assert np.array_equal(original[..., 3], final[..., 3])
    return original, final, c


scene_rgb, aa, coverage = frame(0.37, 0.16, True)
assert np.max(coverage[10:13]) == 0.0
assert np.allclose(np.unique(coverage), [0.0, 0.25, 0.5, 0.75, 1.0], atol=0.002)
assert np.count_nonzero(scene_rgb != aa) > 20
print('PASS shared D24, R8 MSAA 25/50/75% coverage, occluded geometry excluded, unmixed pixels and alpha unchanged')

x_grid, y_grid = np.meshgrid(np.arange(width), np.arange(height))
error_before = error_after = 0.0
for slope in (-0.51, -0.37, 0.23, 0.37, 0.51):
    for phase in np.arange(10) * 0.1:
        original, final, _ = frame(slope, phase)
        reference = np.zeros((height, width))
        for offset in (np.arange(128) + 0.5) / 128:
            reference += np.clip(width / 2 + phase + slope * (y_grid + offset) - x_grid, 0, 1) / 128
        rgb = 0.8 - reference * 0.7
        error_before += np.sum((original[2:-2, :, 0] - rgb[2:-2]) ** 2)
        error_after += np.sum((final[2:-2, :, 0] - rgb[2:-2]) ** 2)
print(f'Diagonal silhouette subpixel error: {error_before:.5f} -> {error_after:.5f}')
assert error_after < error_before * 0.95
