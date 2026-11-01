precision highp float;

// -- Note -- //
// OGL Version: OpenGL ES 2.0


// -- Some TODO -- //
// TODO: Custom uniform;
// TODO: Bloom effect;
// TODO: BOKEH / DOF effect; (My previous DOF broken since i didn't use DepthMap)
// TODO: Anti Aliasing; (No need i guess? since it's 2D Voxels game)
// TODO: 2D SSAO; (WTF I am thinking)
// TODO: Chams for player, item, entity, anything; (Kinda cool thought?)
// TODO: Screen Space Reflection on water; (Should be AMAZING, but i need to learn more about shading techique to implement this feature.)


// --- Textures ---

uniform sampler2D u_sceneTex;       // Current frame
uniform sampler2D u_accumulation;   // Last accumulation frame / Saved frame
uniform vec2 u_resolution; 	    // Screen resolution

// --- Motion Blur & Color Adjust ---

uniform float u_brightness;
uniform float u_contrast;
uniform float u_saturation;
uniform float u_fadeFactor;

// --- God Rays ---

uniform vec2 u_lightPos;
uniform float u_colorTolerance;
uniform float u_exposure;
uniform float u_decay;
uniform float u_density;
uniform float u_weight; 
uniform int u_numSamples;

#define godRaysMix 0.5 // Blend with Post processing;
#define TARGET_COLOR vec4(96.0 / 255.0, 215.0 / 255.0, 242.0 / 255.0, 1.0)


bool isLightSource(vec4 color) {
    vec4 diff = abs(color - TARGET_COLOR);
    return all(lessThanEqual(diff.rgb, vec3(u_colorTolerance)));
}

float computeGodRays(vec2 texCoord) {
    vec2 deltaTexCoord = (u_lightPos - texCoord) * u_density / float(u_numSamples);
    vec2 coord = texCoord;
    float illuminationDecay = 1.0;
    float rayIntensity = 0.0;
    for (int i = 0; i < 256; i++) {
        if (i >= u_numSamples) break;
        vec4 sample = texture2D(u_sceneTex, coord);
        if (isLightSource(sample)) {
            rayIntensity += illuminationDecay * u_weight;
        } else {
            break;
        }
        coord += deltaTexCoord;
        illuminationDecay *= u_decay;
    }
    return rayIntensity * u_exposure;
}

void main() {

    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec4 sceneColor = texture2D(u_sceneTex, uv);
    vec4 prevFrame  = texture2D(u_accumulation, uv);

    // --- Brightness / Contrast / Saturation ---
    vec3 color = sceneColor.rgb;
    color += u_brightness;
    color = (color - 0.5) * u_contrast + 0.5;
    float gray = dot(color, vec3(0.299, 0.587, 0.114));
    color = mix(vec3(gray), color, u_saturation);
    // --- Motion Blur ---
    vec3 blurred = mix(color, prevFrame.rgb, u_fadeFactor);
    // -- God Rays --
    float godRayIntensity = computeGodRays(uv);
	vec3 rayColor = vec3(1.0, 0.85, 0.4);
	vec3 godRaysColor = rayColor * godRayIntensity;
    vec3 finalColor = mix(blurred, blurred + godRaysColor, godRaysMix);

    gl_FragColor = vec4(clamp(finalColor, 0.0, 1.0), sceneColor.a);

}