import * as THREE from 'three'

/**
 * 创建高压门型构架与架空母线走廊系统 (High Voltage Gantries & Overhead Busbars)
 */
export function createGantrySystem() {
  const group = new THREE.Group()
  group.name = 'Substation_GantrySystem'

  const steelMat = new THREE.MeshStandardMaterial({
    color: 0x475569, // 热镀锌角钢格构
    roughness: 0.5,
    metalness: 0.7,
  })
  const insulatorMat = new THREE.MeshStandardMaterial({
    color: 0x7c2d12, // 绝缘子红棕色陶瓷
    roughness: 0.25,
    metalness: 0.1,
  })
  const busbarMat = new THREE.MeshStandardMaterial({
    color: 0x00f0ff, // 科技感母线铝合金管
    roughness: 0.2,
    metalness: 0.9,
    emissive: 0x003344,
    emissiveIntensity: 0.3
  })

  // 创建单榀门型构架 (A-frame gantry)
  const createSingleGantry = (zPos) => {
    const gantry = new THREE.Group()
    gantry.position.z = zPos

    const height = 18
    const span = 44

    // 左右两根主格构立柱 (柱高 18m)
    ;[-span / 2, span / 2].forEach(x => {
      // 主柱圆管
      const poleGeo = new THREE.CylinderGeometry(0.4, 0.7, height, 12)
      const pole = new THREE.Mesh(poleGeo, steelMat)
      pole.position.set(x, height / 2, 0)
      pole.castShadow = true
      gantry.add(pole)

      // 柱脚混凝土基础
      const foundation = new THREE.Mesh(new THREE.BoxGeometry(2.4, 1.2, 2.4), new THREE.MeshStandardMaterial({ color: 0x1e293b }))
      foundation.position.set(x, 0.6, 0)
      gantry.add(foundation)

      // 顶部避雷针 (Lightning Rod)
      const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.15, 3.5, 8), steelMat)
      rod.position.set(x, height + 1.75, 0)
      gantry.add(rod)
    })

    // 顶部承重桁架横梁 (Truss Crossbeam)
    const beamGeo = new THREE.BoxGeometry(span + 2, 0.7, 0.7)
    const beam = new THREE.Mesh(beamGeo, steelMat)
    beam.position.y = height - 0.5
    gantry.add(beam)

    // 悬挂式三相瓷绝缘子串 (3相：左、中、右)
    ;[-14, 0, 14].forEach(x => {
      const insGroup = new THREE.Group()
      insGroup.position.set(x, height - 1.0, 0)

      // 串珠式绝缘子盘 (10片)
      for (let i = 0; i < 10; i++) {
        const disc = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.2, 0.12, 12), insulatorMat)
        disc.position.y = -i * 0.22
        insGroup.add(disc)
      }

      // 金具与导线挂线夹
      const clamp = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.2, 0.3), steelMat)
      clamp.position.y = -2.3
      insGroup.add(clamp)

      gantry.add(insGroup)
    })

    return gantry
  }

  // 建设前中后三榀高压架构
  const gantry1 = createSingleGantry(-28)
  const gantry2 = createSingleGantry(0)
  const gantry3 = createSingleGantry(28)
  group.add(gantry1)
  group.add(gantry2)
  group.add(gantry3)

  // 纵向贯穿全站的三相架空高压母线 (A/B/C 三相)
  ;[-14, 0, 14].forEach(x => {
    const busGeo = new THREE.CylinderGeometry(0.12, 0.12, 70, 16)
    busGeo.rotateX(Math.PI / 2)
    const busbar = new THREE.Mesh(busGeo, busbarMat)
    busbar.position.set(x, 15.6, 0)
    group.add(busbar)
  })

  return group
}
