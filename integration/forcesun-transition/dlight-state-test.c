#include "tr_local.h"
#include <assert.h>

static vec4_t environmentContribution;
static vec4_t enabledTextures;

void GLSL_SetUniformVec4(shaderProgram_t *program, int uniform, const vec4_t value)
{
    assert(program);
    switch (uniform)
    {
        case UNIFORM_ENABLETEXTURES:
            VectorCopy4(value, enabledTextures);
            break;
        case UNIFORM_INDIRECTLIGHTPARAMS:
            VectorCopy4(value, environmentContribution);
            break;
        default:
            assert(!"Unexpected uniform in the point-light environment setup");
    }
}

static void beginPointLight(shaderProgram_t *sp)
{
    /* POINT_LIGHT_ENVIRONMENT_SETUP */
}

int main(void)
{
    shaderProgram_t program = {0};
    const vec4_t environment = {0.18f, 0.65f, 0.18f, 0.0f};
    const vec4_t materialTextures = {1.0f, 1.0f, 1.0f, 1.0f};

    // The preceding material draw used this same shader program.
    GLSL_SetUniformVec4(&program, UNIFORM_INDIRECTLIGHTPARAMS, environment);
    GLSL_SetUniformVec4(&program, UNIFORM_ENABLETEXTURES, materialTextures);
    beginPointLight(&program);

    for (int channel = 0; channel < 4; ++channel)
    {
        assert(environmentContribution[channel] == 0.0f);
        assert(enabledTextures[channel] == 0.0f);
    }
    puts("PASS point-light draw clears the previous material's environment uniforms");
    return 0;
}
