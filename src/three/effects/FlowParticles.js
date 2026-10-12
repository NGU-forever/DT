import * as THREE from 'three'

/**
 * 变电站高压电流/能量流动粒子系统 (Electric Flow Particles)
 */
export class FlowParticles {
  constructor(scene) {
    this.scene = scene
    this.particleCountPerLine = 45
    this.paths = []
    this.particleSystems = []
    this.speeds = []
    this.active = true

    this.initPaths()
    this.createParticles()
  }

  initPaths() {
    // 路径1: 进线高压架构 -> 1# 主变高压套管 (3相)
    const line1A = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-14, 15.6, -28),
      new THREE.Vector3(-14, 15.6, -10),
      new THREE.Vector3(-25, 13.0, 5),
      new THREE.Vector3(-22.4, 12.0, 11.2) // 1# 主变 A 相
    ])
    const line1B = new THREE.CatmullRomCurve3([
      new THREE.Vector3(0, 15.6, -28),
      new THREE.Vector3(-5, 15.6, -10),
      new THREE.Vector3(-20, 13.0, 5),
      new THREE.Vector3(-20.0, 12.0, 11.2) // 1# 主变 B 相
    ])
    const line1C = new THREE.CatmullRomCurve3([
      new THREE.Vector3(14, 15.6, -28),
      new THREE.Vector3(5, 15.6, -10),
      new THREE.Vector3(-15, 13.0, 5),
      new THREE.Vector3(-17.6, 12.0, 11.2) // 1# 主变 C 相
    ])

    // 路径2: 1# 主变低压侧 -> GIS 201 进线断路器
    const line2 = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-20, 10.0, 8.7),
      new THREE.Vector3(-20, 8.5, 0),
      new THREE.Vector3(-10, 7.5, -15),
      new THREE.Vector3(10, 7.4, -15),
      new THREE.Vector3(20, 6.2, -15) // GIS 201
    ])

    // 路径3: GIS 201 -> 110kV GIS 101 出线
    const line3 = new THREE.CatmullRomCurve3([
      new THREE.Vector3(20, 6.2, -15),
      new THREE.Vector3(35, 6.2, -15),
      new THREE.Vector3(45, 10.0, -5),
      new THREE.Vector3(50, 14.0, 15)
    ])

    this.paths = [
      { curve: line1A, speed: 0.22, color: 0x00f0ff, key: 'main' },
      { curve: line1B, speed: 0.22, color: 0x00f0ff, key: 'main' },
      { curve: line1C, speed: 0.22, color: 0x00f0ff, key: 'main' },
      { curve: line2, speed: 0.18, color: 0x00e5ff, key: 'gis' },
      { curve: line3, speed: 0.24, color: 0x00ffcc, key: 'out' }
    ]
  }

  createParticles() {
    this.paths.forEach((pathObj, idx) => {
      const geometry = new THREE.BufferGeometry()
      const positions = new Float32Array(this.particleCountPerLine * 3)
      const uProgress = new Float32Array(this.particleCountPerLine)

      for (let i = 0; i < this.particleCountPerLine; i++) {
        const u = i / this.particleCountPerLine
        uProgress[i] = u
        const point = pathObj.curve.getPointAt(u)
        positions[i * 3] = point.x
        positions[i * 3 + 1] = point.y
        positions[i * 3 + 2] = point.z
      }

      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))

      // 粒子材质
      const material = new THREE.PointsMaterial({
        color: pathObj.color,
        size: 0.65,
        transparent: true,
        opacity: 0.85,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      })

      const pointMesh = new THREE.Points(geometry, material)
      pointMesh.name = `flow_particles_${idx}`
      this.scene.add(pointMesh)

      this.particleSystems.push({
        mesh: pointMesh,
        curve: pathObj.curve,
        uProgress: uProgress,
        speed: pathObj.speed,
        key: pathObj.key,
      })
    })
  }

  update(delta) {
    if (!this.active) return

    this.particleSystems.forEach((sys) => {
      const positions = sys.mesh.geometry.attributes.position.array
      const len = sys.uProgress.length

      for (let i = 0; i < len; i++) {
        sys.uProgress[i] += sys.speed * delta
        if (sys.uProgress[i] > 1.0) {
          sys.uProgress[i] -= 1.0
        }

        const pt = sys.curve.getPointAt(sys.uProgress[i])
        positions[i * 3] = pt.x
        positions[i * 3 + 1] = pt.y
        positions[i * 3 + 2] = pt.z
      }

      sys.mesh.geometry.attributes.position.needsUpdate = true
    })
  }

  setActive(isActive) {
    this.active = isActive
    this.particleSystems.forEach(sys => {
      sys.mesh.visible = isActive
    })
  }

  // 根据断路器分闸状态停流对应分支
  setLineActive(key, isActive) {
    this.particleSystems.forEach(sys => {
      if (sys.key === key) {
        sys.mesh.visible = isActive && this.active
      }
    })
  }
}
