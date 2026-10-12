import * as THREE from 'three'

/**
 * 红外热成像伪彩色渐变着色器材质 (Infrared Heatmap Shader)
 * 采用经典工业热像仪测温色谱：深蓝(低温) -> 青 -> 绿 -> 黄 -> 橙 -> 艳红(过热)
 */
export function createHeatmapMaterial(minTemp = 30, maxTemp = 100) {
  return new THREE.ShaderMaterial({
    uniforms: {
      uMinTemp: { value: minTemp },
      uMaxTemp: { value: maxTemp },
      uCurrentTemp: { value: 65.0 },
      uTime: { value: 0 }
    },
    vertexShader: `
      varying vec3 vPosition;
      varying vec3 vNormal;
      void main() {
        vPosition = position;
        vNormal = normalize(normalMatrix * normal);
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform float uMinTemp;
      uniform float uMaxTemp;
      uniform float uCurrentTemp;
      uniform float uTime;
      varying vec3 vPosition;
      varying vec3 vNormal;

      // 热像调色板插值
      vec3 getThermalColor(float val) {
        val = clamp(val, 0.0, 1.0);
        vec3 c1 = vec3(0.05, 0.1, 0.4);   // 深蓝
        vec3 c2 = vec3(0.0, 0.8, 0.8);    // 青色
        vec3 c3 = vec3(0.2, 0.9, 0.1);    // 绿色
        vec3 c4 = vec3(1.0, 0.85, 0.0);   // 金黄
        vec3 c5 = vec3(1.0, 0.15, 0.1);   // 亮红

        if (val < 0.25) return mix(c1, c2, val * 4.0);
        if (val < 0.5) return mix(c2, c3, (val - 0.25) * 4.0);
        if (val < 0.75) return mix(c3, c4, (val - 0.5) * 4.0);
        return mix(c4, c5, (val - 0.75) * 4.0);
      }

      void main() {
        // 基于高度与中心距离模拟变压器内部发热梯度
        float distFactor = 1.0 - length(vPosition.xz) * 0.12;
        float heightFactor = smoothstep(-2.0, 3.0, vPosition.y);
        float tempVal = (uCurrentTemp - uMinTemp) / (uMaxTemp - uMinTemp);
        float localTemp = tempVal * (distFactor * 0.7 + heightFactor * 0.3);

        vec3 thermalColor = getThermalColor(localTemp);

        // 简易光照漫反射与边缘高光
        float diff = max(dot(vNormal, vec3(0.0, 1.0, 0.5)), 0.35);
        gl_FragColor = vec4(thermalColor * diff, 0.92);
      }
    `,
    transparent: true,
  })
}
