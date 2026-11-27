"""Exercise the actual Rend2 raymarch shaders with synthetic inputs in Mesa EGL."""
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
from OpenGL import EGL, GL
from OpenGL.GL.shaders import compileProgram, compileShader

parser = ArgumentParser(description='Exercise the LocalVol lamp composite on Mesa EGL.')
parser.add_argument('patched_source', type=Path)
parser.add_argument('baseline_source', type=Path)
args = parser.parse_args()
shader = args.patched_source / 'SP/code/rend2/glsl'
width, height = 48, 36

display = EGL.eglGetDisplay(EGL.EGL_DEFAULT_DISPLAY)
major, minor, count = EGL.EGLint(), EGL.EGLint(), EGL.EGLint()
assert EGL.eglInitialize(display, major, minor)
assert EGL.eglBindAPI(EGL.EGL_OPENGL_API)
attributes = (EGL.EGLint * 9)(
    EGL.EGL_SURFACE_TYPE, EGL.EGL_PBUFFER_BIT,
    EGL.EGL_RENDERABLE_TYPE, EGL.EGL_OPENGL_BIT,
    EGL.EGL_RED_SIZE, 8, EGL.EGL_GREEN_SIZE, 8, EGL.EGL_NONE,
)
configs = (EGL.EGLConfig * 1)()
assert EGL.eglChooseConfig(display, attributes, configs, 1, count) and count.value
surface_attributes = (EGL.EGLint * 5)(EGL.EGL_WIDTH, width, EGL.EGL_HEIGHT, height, EGL.EGL_NONE)
surface = EGL.eglCreatePbufferSurface(display, configs[0], surface_attributes)
context = EGL.eglCreateContext(display, configs[0], EGL.EGL_NO_CONTEXT, None)
assert EGL.eglMakeCurrent(display, surface, surface, context)
print('OpenGL', GL.glGetString(GL.GL_VERSION).decode(), GL.glGetString(GL.GL_RENDERER).decode())


def compile_pair(vertex, fragment):
    return compileProgram(compileShader(vertex, GL.GL_VERTEX_SHADER),
                          compileShader(fragment, GL.GL_FRAGMENT_SHADER), validate=False)

def local_program(directory, coverage=False):
    options = '#define M_PI 3.14159265358979323846\n'
    if coverage:
        options += '#define USE_LOCAL_MULTISAMPLE_COVERAGE\n'
    vertex = (directory / 'volumetriclocal_vp.glsl').read_text()
    if not coverage:
        # Use upright framebuffer coordinates for the analytic near/far reference.
        vertex = vertex.replace('u_ViewUp * -screenCoords.y', 'u_ViewUp * screenCoords.y')
    fragment = (directory / 'volumetriclocal_fp.glsl').read_text()
    return compile_pair(
        '#version 150\n#define attribute in\n#define varying out\n' + options + vertex,
        '#version 150\n#define varying in\nout vec4 out_Color;\n#define gl_FragColor out_Color\n'
        '#define texture2D texture\n#define textureCubeLod textureLod\n' + options + fragment,
    )


lamp_coverage = local_program(shader, coverage=True)
legacy = local_program(shader)
accepted = local_program(args.baseline_source / 'SP/code/rend2/glsl')
quad = np.array([[-1,-1,0,1], [1,-1,0,1], [-1,1,0,1], [1,1,0,1]], dtype='f4')
uvs = ((quad[:, :2] + 1) * 0.5).copy()
def draw(program):
    for name, array in [('attr_Position', quad), ('attr_TexCoord0', uvs)]:
        location = GL.glGetAttribLocation(program, name)
        if location >= 0:
            GL.glEnableVertexAttribArray(location)
            GL.glVertexAttribPointer(location, array.shape[1], GL.GL_FLOAT, False, 0, array)
    GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)

def texture2d(unit, internal, pixels, fmt, sizes=(width, height)):
    GL.glActiveTexture(GL.GL_TEXTURE0 + unit)
    texture = GL.glGenTextures(1)
    GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
    GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
    GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, internal, *sizes, 0, fmt, GL.GL_FLOAT, pixels)
    return texture

output = texture2d(7, GL.GL_RGBA32F, None, GL.GL_RGBA)
color = texture2d(0, GL.GL_RGBA32F, np.full((height,width,4),0.28,dtype='f4'), GL.GL_RGBA)
depth_2d = texture2d(2, GL.GL_DEPTH_COMPONENT24, None, GL.GL_DEPTH_COMPONENT)
out_fbo = GL.glGenFramebuffers(1)
GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, out_fbo)
GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, output, 0)
assert GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER) == GL.GL_FRAMEBUFFER_COMPLETE

# Exact coverage fixture using the same color renderbuffer and depth texture formats as Rend2.
ms_fbo = GL.glGenFramebuffers(1)
GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, ms_fbo)
ms_color = GL.glGenRenderbuffers(1)
GL.glBindRenderbuffer(GL.GL_RENDERBUFFER, ms_color)
GL.glRenderbufferStorageMultisample(GL.GL_RENDERBUFFER, 4, GL.GL_RGBA16F,width,height)
GL.glFramebufferRenderbuffer(GL.GL_FRAMEBUFFER,GL.GL_COLOR_ATTACHMENT0,GL.GL_RENDERBUFFER,ms_color)
GL.glActiveTexture(GL.GL_TEXTURE2)
depth_ms = GL.glGenTextures(1)
GL.glBindTexture(GL.GL_TEXTURE_2D_MULTISAMPLE,depth_ms)
GL.glTexImage2DMultisample(GL.GL_TEXTURE_2D_MULTISAMPLE,4,GL.GL_DEPTH_COMPONENT24,width,height,True)
GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER,GL.GL_DEPTH_ATTACHMENT,GL.GL_TEXTURE_2D_MULTISAMPLE,depth_ms,0)
assert GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER) == GL.GL_FRAMEBUFFER_COMPLETE
assert GL.glGetTexLevelParameteriv(GL.GL_TEXTURE_2D_MULTISAMPLE,0,GL.GL_TEXTURE_SAMPLES)==4

stamp=compile_pair('#version 150\nin vec4 attr_Position;void main(){gl_Position=attr_Position;}',
                   '#version 150\nuniform float z;out vec4 value;void main(){gl_FragDepth=z;value=vec4(0);}')
near_z, far_z = np.float32(0.60), np.float32(0.997)
GL.glEnable(GL.GL_MULTISAMPLE)
GL.glEnable(GL.GL_DEPTH_TEST)
GL.glDepthFunc(GL.GL_ALWAYS)
GL.glViewport(0,0,width,height)
GL.glUseProgram(stamp)
GL.glUniform1f(GL.glGetUniformLocation(stamp,'z'),far_z)
draw(stamp)
GL.glUniform1f(GL.glGetUniformLocation(stamp,'z'),near_z)
GL.glEnable(GL.GL_SCISSOR_TEST)
GL.glScissor(0,0,12,height)
draw(stamp)
GL.glScissor(12,0,24,height)
GL.glEnable(GL.GL_SAMPLE_MASK)
# Across the sloped staircase diagnostic, the real depth sample coverage varies.
for index, bitmask in enumerate((1,3,7)):
    GL.glScissor(12 + index*8,0,8,height)
    GL.glSampleMaski(0,bitmask)
    draw(stamp)
GL.glDisable(GL.GL_SAMPLE_MASK)
GL.glDisable(GL.GL_SCISSOR_TEST)
GL.glDisable(GL.GL_DEPTH_TEST)

# Mesa must also support the renderer's unchanged color + depth resolve.
resolved = GL.glGenFramebuffers(1)
GL.glBindFramebuffer(GL.GL_FRAMEBUFFER,resolved)
resolved_color = texture2d(7,GL.GL_RGBA16F,None,GL.GL_RGBA)
GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER,GL.GL_COLOR_ATTACHMENT0,GL.GL_TEXTURE_2D,resolved_color,0)
GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER,GL.GL_DEPTH_ATTACHMENT,GL.GL_TEXTURE_2D,depth_2d,0)
assert GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER)==GL.GL_FRAMEBUFFER_COMPLETE
GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER,ms_fbo)
GL.glBlitFramebuffer(0,0,width,height,0,0,width,height,GL.GL_COLOR_BUFFER_BIT|GL.GL_DEPTH_BUFFER_BIT,GL.GL_NEAREST)
assert GL.glGetError()==GL.GL_NO_ERROR

def upload_depth(data):
    GL.glActiveTexture(GL.GL_TEXTURE2)
    GL.glBindTexture(GL.GL_TEXTURE_2D,depth_2d)
    GL.glTexSubImage2D(GL.GL_TEXTURE_2D,0,0,0,width,height,GL.GL_DEPTH_COMPONENT,GL.GL_FLOAT,data)

def render(program, mode=2, viewport=(0, 0, width, height), jitter=0.0):
    x, y, w, h = viewport
    rect = (x / width, y / height, w / width, h / height)
    uvs[:] = ((quad[:, :2] + 1) * 0.5) * rect[2:] + rect[:2]
    GL.glViewport(*viewport)
    GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, out_fbo)
    GL.glUseProgram(program)

    def uniform(name):
        return GL.glGetUniformLocation(program, name)

    GL.glUniformMatrix4fv(uniform('u_ModelViewProjectionMatrix'), 1, False, np.eye(4, dtype='f4'))
    for name, unit in {
        'u_ScreenDepthMap': 2, 'u_TextureMap': 0, 'u_DlightShadowMap': 6, 'u_DlightWorldMap': 1,
    }.items():
        GL.glUniform1i(uniform(name), unit)
    settings = {
        'u_InvTexRes': (1 / width, 1 / height), 'u_ViewInfo': (150, 600, 0.7, 1),
        'u_LocalViewRect': rect, 'u_LocalCoverageInfo': (4, width / 2, height / 2),
        'u_ViewForward': (600, 0, 0), 'u_ViewLeft': (0, 330, 0), 'u_ViewUp': (0, 0, 250),
        'u_ViewOrigin': (0, 0, 0), 'u_PrimaryLightOrigin': (165, 0, 0, 135),
        'u_CubeMapInfo': (165, 0, -18, 98), 'u_PrimaryLightColor': (1, 0.85, 0.4),
        'u_Color': (1.1, 0.0045, 0.2, 600),
        'u_BaseColor': (9, 0.1, 0.42 if mode >= 5 else 0.98, 0.9),
        'u_EnableTextures': (32, 2, jitter, mode),
        'u_DlightInfo': (-1, 0, 0, 0.60) if mode == 4 else (0.5, 1, 135, 0),
        'u_DlightShadowParams': (0, 0.0033, 0.008, 0.88), 'u_DlightWorldOrigin': (0, 0, 0, 0),
    }
    for name, value in settings.items():
        getattr(GL, f'glUniform{len(value)}f')(uniform(name), *value)
    draw(program)
    pixels = GL.glReadPixels(x, y, w, h, GL.GL_RGBA, GL.GL_FLOAT)
    return np.frombuffer(pixels, dtype='f4').copy().reshape(h, w, 4)[..., :3]


def set_depth(value):
    upload_depth(np.full((height, width), value, dtype='f4'))


read_coverage = compile_pair(
    '#version 150\nin vec4 attr_Position;void main(){gl_Position=attr_Position;}',
    '#version 150\nuniform sampler2DMS u_ScreenDepthMap;out vec4 value;'
    'void main(){ivec2 p=ivec2(gl_FragCoord.xy);float c=0.0;'
    'for(int i=0;i<4;++i)c+=float(texelFetch(u_ScreenDepthMap,p,i).r<0.8);value=vec4(c*0.25);}',
)
for viewport in ((0, 0, width, height), (5, 4, 35, 27)):
    weights = render(read_coverage, viewport=viewport)[..., 0]
    assert {0.25, 0.5, 0.75}.issubset(set(np.unique(weights)))
    mixed = (weights > 0) & (weights < 1)
    for mode in (1, 2, 3):
        set_depth(near_z)
        near = render(legacy, mode, viewport)
        set_depth(far_z)
        far = render(legacy, mode, viewport)
        assert np.max(far[mixed] - near[mixed]) > 0.08
        observed = render(lamp_coverage, mode, viewport)
        oracle = near * weights[..., None] + far * (1 - weights[..., None])
        assert np.max(np.abs(oracle[mixed] - observed[mixed])) < 4e-5
        assert np.allclose(observed[~mixed], 0.28, atol=2e-6)
        for ratio in (0.25, 0.5, 0.75):
            assert (observed[weights == ratio] > near[weights == ratio]).any()
print('PASS real 4xMSAA: 25/50/75% foreground, modes 1/2/3, full and offset viewport')
print('PASS all unmixed pixels preserve reconstructed light')

# Include the shared FireVol/spotlight branches with live jitter.
for mode in range(1, 10):
    for depth in (near_z, far_z):
        set_depth(depth)
        before = render(accepted, mode, jitter=0.08)
        after = render(legacy, mode, jitter=0.08)
        if depth == far_z:
            assert before.max() > 0.01, mode
        assert np.isfinite(after).all() and np.allclose(before, after, atol=2e-6, rtol=0), mode
print('PASS original lamp, spotlight and fire raymarch modes 1–9 preserve their output')
