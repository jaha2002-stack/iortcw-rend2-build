uniform sampler2D u_DiffuseMap;
uniform samplerCube u_ShadowMap;

uniform int u_AlphaTest;

uniform vec4 u_LightOrigin;
uniform float u_LightRadius;

uniform int u_DlightShadowMode;
uniform vec4 u_DlightShadowParams;
uniform float u_DlightShadowBias;

varying vec2 var_Tex1;
varying vec4 var_Color;
varying vec3 var_WorldPos;

float DecodeLinearDistance24(vec3 enc)
{
    return clamp(dot(enc, vec3(1.0 / (256.0 * 256.0), 1.0 / 256.0, 1.0)), 0.0, 1.0);
}

void main()
{
    vec4 color = texture2D(u_DiffuseMap, var_Tex1);
    float alpha = color.a * var_Color.a;

    if (u_AlphaTest == 1)
    {
        if (alpha == 0.0) discard;
    }
    else if (u_AlphaTest == 2)
    {
        if (alpha >= 0.5) discard;
    }
    else if (u_AlphaTest == 3)
    {
        if (alpha < 0.5) discard;
    }

    vec3 outRgb = color.rgb * var_Color.rgb;

    if (u_DlightShadowMode > 0)
    {
        vec3 lightToFrag = var_WorldPos - u_LightOrigin.xyz;
        float dist = length(lightToFrag);
        float farPlane = max(u_DlightShadowParams.y, 1.0);
        float strength = clamp(u_DlightShadowParams.z, 0.0, 1.0);
        float debugScale = max(u_DlightShadowParams.w, 0.001);

        vec3 dir = lightToFrag;
        if (dot(dir, dir) < 0.0001)
        {
            dir = vec3(0.0, 0.0, 1.0);
        }

        vec4 cubeSample = texture(u_ShadowMap, dir);
        float storedLinear = DecodeLinearDistance24(cubeSample.rgb);
        float currentLinear = clamp(dist / farPlane, 0.0, 1.0);

        if (u_DlightShadowMode == 1)
        {
            outRgb *= (1.0 - strength);
        }
        else if (u_DlightShadowMode == 2)
        {
            float v = clamp(currentLinear * debugScale, 0.0, 1.0);
            outRgb *= vec3(v, 1.0 - v, 0.25);
        }
        else if (u_DlightShadowMode == 3)
        {
            outRgb *= cubeSample.rgb;
        }
        else if (u_DlightShadowMode == 4)
        {
            float shadowFactor = ((currentLinear - u_DlightShadowBias) > storedLinear) ? (1.0 - strength) : 1.0;
            outRgb *= shadowFactor;
        }
        else if (u_DlightShadowMode == 5)
        {
            float diff = (currentLinear - u_DlightShadowBias) - storedLinear;
            float shadowAmount = smoothstep(0.0, 0.035, diff) * strength;
            outRgb *= (1.0 - shadowAmount);
        }
        else if (u_DlightShadowMode == 6)
        {
            float shadowFactor = ((currentLinear + u_DlightShadowBias) < storedLinear) ? (1.0 - strength) : 1.0;
            outRgb *= shadowFactor;
        }
        else if (u_DlightShadowMode == 7)
        {
            float v = clamp(storedLinear * debugScale, 0.0, 1.0);
            outRgb *= vec3(v);
        }
        else if (u_DlightShadowMode == 8)
        {
            vec3 nDir = normalize(dir);
            vec3 pattern = vec3(nDir.x > 0.0 ? 1.0 : 0.25,
                                nDir.y > 0.0 ? 1.0 : 0.25,
                                nDir.z > 0.0 ? 1.0 : 0.25);
            outRgb *= pattern;
        }
    }

    gl_FragColor.rgb = outRgb;
    gl_FragColor.a = alpha;
}
