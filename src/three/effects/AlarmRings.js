import * as THREE from 'three'

/**
 * 设备异常/故障告警动态扩散光环 (Alarm Pulse Rings)
 */
export class AlarmRings {
  constructor(scene) {
    this.scene = scene
    this.rings = []
  }

  /**
   * 为指定设备坐标附加告警光环
   * @param {string} id 标识
   * @param {THREE.Vector3} position 设备地面中心坐标
   * @param {number} color 颜色十六进制 (默认深红 0xff0044)
   */
  addAlarm(id, position, color = 0xff0044) {
    // 移除已有
    this.removeAlarm(id)

    const group = new THREE.Group()
    group.position.set(position.x, 0.4, position.z)

    // 创建内外两层波纹环
    const ringGeo = new THREE.RingGeometry(2.5, 3.2, 32)
    ringGeo.rotateX(-Math.PI / 2)

    const ringMat = new THREE.MeshBasicMaterial({
      color: color,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    })

    const ringMesh1 = new THREE.Mesh(ringGeo, ringMat)
    group.add(ringMesh1)

    const ringMesh2 = new THREE.Mesh(ringGeo, ringMat.clone())
    ringMesh2.scale.set(0.5, 0.5, 0.5)
    group.add(ringMesh2)

    // 垂直光柱 (Cylinder Light Beam)
    const beamGeo = new THREE.CylinderGeometry(2.8, 2.8, 16, 24, 1, true)
    const beamMat = new THREE.MeshBasicMaterial({
      color: color,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.25,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    })
    const beamMesh = new THREE.Mesh(beamGeo, beamMat)
    beamMesh.position.y = 8
    group.add(beamMesh)

    this.scene.add(group)

    this.rings.push({
      id,
      group,
      ring1: ringMesh1,
      ring2: ringMesh2,
      beam: beamMesh,
      time: 0
    })
  }

  removeAlarm(id) {
    const idx = this.rings.findIndex(r => r.id === id)
    if (idx !== -1) {
      const item = this.rings[idx]
      this.scene.remove(item.group)
      this.rings.splice(idx, 1)
    }
  }

  clearAll() {
    this.rings.forEach(item => {
      this.scene.remove(item.group)
    })
    this.rings = []
  }

  update(delta) {
    this.rings.forEach(item => {
      item.time += delta * 2.2

      // 环1 扩散缩放与渐隐
      const scale1 = 1 + (item.time % 2.5) * 1.5
      item.ring1.scale.set(scale1, scale1, scale1)
      item.ring1.material.opacity = Math.max(0, 0.8 - (item.time % 2.5) * 0.3)

      // 环2 错开相位
      const scale2 = 1 + ((item.time + 1.25) % 2.5) * 1.5
      item.ring2.scale.set(scale2, scale2, scale2)
      item.ring2.material.opacity = Math.max(0, 0.8 - ((item.time + 1.25) % 2.5) * 0.3)

      // 光柱微幅呼吸
      item.beam.material.opacity = 0.2 + Math.sin(item.time * 3) * 0.1
    })
  }
}
