uniform vec4 u_LightOrigin;
uniform float u_LightRadius;

varying vec3 var_Position;

vec3 EncodeLinearDistance24(float depth)
{
    depth = clamp(depth, 0.0, 1.0);

    const vec3 bitSh = vec3(256.0 * 256.0, 256.0, 1.0);
    const vec3 bitMsk = vec3(0.0, 1.0 / 256.0, 1.0 / 256.0);

    vec3 comp = depth * bitSh;
    comp.xy = fract(comp.xy);
    comp -= comp.xxy * bitMsk;

    return comp;
}

void main()
{
    float radius = max(u_LightRadius, 1.0);
    float depth = length(u_LightOrigin.xyz - var_Position) / radius;

    gl_FragColor = vec4(EncodeLinearDistance24(depth), 1.0);
}
