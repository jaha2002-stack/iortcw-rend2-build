// DARKWOLF_ADAPTIVE_GLASS_V1; built into renderer (no external PK3 required).
attribute vec3 attr_Position;
attribute vec3 attr_Normal;
attribute vec4 attr_TexCoord0;
uniform mat4 u_ModelViewProjectionMatrix;
uniform mat4 u_ModelMatrix;
varying vec3 v_DWGlassWorldPos;
varying vec3 v_DWGlassWorldNormal;
varying vec2 v_DWGlassTex;
void main() {
    vec4 world = u_ModelMatrix * vec4(attr_Position, 1.0);
    v_DWGlassWorldPos = world.xyz;
    v_DWGlassWorldNormal = normalize(mat3(u_ModelMatrix) * attr_Normal);
    v_DWGlassTex = attr_TexCoord0.st;
    gl_Position = u_ModelViewProjectionMatrix * vec4(attr_Position, 1.0);
}
