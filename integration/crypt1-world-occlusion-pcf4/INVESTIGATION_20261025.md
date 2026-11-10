# Crypt1 architectural shadow

October's world visibility map uses 256 cubemap texels per face and a hard step depth comparison. Tests on Crypt1 confirmed this stage affects 0.98-1.64% of rendered pixels with PCF4. The fail-closed V02 kernel is insufficient; it retains the nearest-texel shadow boundary. The official clean release stays unchanged until an actual Crypt1 and Escape1 regression passes.
