import * as THREE from 'three'
import TWEEN from '@tweenjs/tween.js'

/**
 * 创建 220kV 主变压器精细模型
 * @param {string} deviceId 设备标识 (如 'trans-1', 'trans-2')
 * @param {THREE.Vector3} position 坐标位置
 * @param {string} label 设备名称
 */
export function createTransformer(deviceId, position, label = '1# 主变压器') {
  const root = new THREE.Group()
  root.position.copy(position)
  root.name = deviceId

  // 可交互设备元数据
  root.userData = {
    isDevice: true,
    deviceId: deviceId,
    name: label,
    type: 'transformer'
  }

  // 拆解动画部件注册
  const explodableParts = {
    tankLid: null,
    tankBody: null,
    coreAndWindings: null,
    radiatorLeft: null,
    radiatorRight: null,
    conservator: null,
    bushings: null,
  }

  // 基础标准材质
  const tankMat = new THREE.MeshStandardMaterial({
    color: 0x3d4a5d,
    roughness: 0.45,
    metalness: 0.55,
  })
  const metalAccentMat = new THREE.MeshStandardMaterial({
    color: 0x7a8b9e,
    roughness: 0.3,
    metalness: 0.8,
  })
  const porcelainMat = new THREE.MeshStandardMaterial({
    color: 0x6e261e, // 棕红色绝缘陶瓷套管
    roughness: 0.2,
    metalness: 0.1,
  })
  const brassMat = new THREE.MeshStandardMaterial({
    color: 0xd4af37,
    roughness: 0.3,
    metalness: 0.85,
  })
  const coreMat = new THREE.MeshStandardMaterial({
    color: 0x2b303c, // 硅钢片铁芯
    roughness: 0.6,
    metalness: 0.7,
  })
  const copperMat = new THREE.MeshStandardMaterial({
    color: 0xb86d29, // 纯铜线圈绕组
    roughness: 0.35,
    metalness: 0.75,
  })

  // 1. 变压器水泥基础台与事故油坑鹅卵石 (Base Foundation)
  const baseGeo = new THREE.BoxGeometry(16, 1.2, 14)
  const baseMat = new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.9 })
  const baseMesh = new THREE.Mesh(baseGeo, baseMat)
  baseMesh.position.y = 0.6
  baseMesh.receiveShadow = true
  root.add(baseMesh)

  // 碎石储油坑边框
  const curbGeo = new THREE.BoxGeometry(17, 0.4, 15)
  const curbMesh = new THREE.Mesh(curbGeo, new THREE.MeshStandardMaterial({ color: 0x374151 }))
  curbMesh.position.y = 0.2
  root.add(curbMesh)

  // 2. 内部结构：硅钢片铁芯与高低压线圈 (Core & Windings)
  const coreGroup = new THREE.Group()
  coreGroup.position.y = 4.8

  // 三相铁芯柱 (Three-limb Core)
  const limbGeo = new THREE.CylinderGeometry(0.8, 0.8, 4.6, 16)
  const yokeGeo = new THREE.BoxGeometry(6.6, 0.9, 1.7)

  // 上下铁轭
  const yokeBottom = new THREE.Mesh(yokeGeo, coreMat)
  yokeBottom.position.y = -2.1
  coreGroup.add(yokeBottom)
  const yokeTop = new THREE.Mesh(yokeGeo, coreMat)
  yokeTop.position.y = 2.1
  coreGroup.add(yokeTop)

  // A, B, C 三相线圈与铁心柱
  ;[-2.2, 0, 2.2].forEach((xOffset, idx) => {
    // 铁芯柱
    const limb = new THREE.Mesh(limbGeo, coreMat)
    limb.position.x = xOffset
    coreGroup.add(limb)

    // 内部同心圆柱铜线圈
    const coilGeo = new THREE.CylinderGeometry(1.25, 1.25, 3.2, 24)
    const coil = new THREE.Mesh(coilGeo, copperMat)
    coil.position.x = xOffset
    coreGroup.add(coil)

    // 线圈绝缘匝道光环装饰
    for (let h = -1.2; h <= 1.2; h += 0.8) {
      const ringGeo = new THREE.TorusGeometry(1.28, 0.05, 8, 24)
      const ring = new THREE.Mesh(ringGeo, brassMat)
      ring.rotation.x = Math.PI / 2
      ring.position.set(xOffset, h, 0)
      coreGroup.add(ring)
    }
  })
  root.add(coreGroup)
  explodableParts.coreAndWindings = coreGroup

  // 3. 变压器主油箱箱体 (Main Tank Body)
  const tankBodyGroup = new THREE.Group()
  tankBodyGroup.position.y = 4.8

  const tankGeo = new THREE.BoxGeometry(8.2, 5.8, 5.2)
  const tankMesh = new THREE.Mesh(tankGeo, tankMat)
  tankMesh.castShadow = true
  tankMesh.receiveShadow = true
  tankBodyGroup.add(tankMesh)

  // 箱体加强筋 (Stiffeners)
  for (let y = -2; y <= 2; y += 1.3) {
    const stiffGeo = new THREE.BoxGeometry(8.5, 0.15, 5.4)
    const stiff = new THREE.Mesh(stiffGeo, metalAccentMat)
    stiff.position.y = y
    tankBodyGroup.add(stiff)
  }

  // 设备铭牌 (Nameplate)
  const plateGeo = new THREE.PlaneGeometry(1.6, 1.0)
  const plateMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff })
  const plate = new THREE.Mesh(plateGeo, plateMat)
  plate.position.set(0, 0.5, 2.62)
  tankBodyGroup.add(plate)

  root.add(tankBodyGroup)
  explodableParts.tankBody = tankBodyGroup

  // 4. 箱盖与高低压套管 (Lid & Bushings)
  const lidGroup = new THREE.Group()
  lidGroup.position.y = 7.8

  const lidGeo = new THREE.BoxGeometry(8.6, 0.4, 5.6)
  const lidMesh = new THREE.Mesh(lidGeo, metalAccentMat)
  lidGroup.add(lidMesh)

  // 220kV 高压侧绝缘套管 (3基 A/B/C 相，倾斜挺拔)
  const bushingGroup = new THREE.Group()
  ;[-2.4, 0, 2.4].forEach((xPos, idx) => {
    const singleBushing = new THREE.Group()
    singleBushing.position.set(xPos, 0.2, 1.2)
    singleBushing.rotation.x = 0.18 // 稍微外倾

    // 升高座筒体
    const turretGeo = new THREE.CylinderGeometry(0.5, 0.55, 0.8, 16)
    const turret = new THREE.Mesh(turretGeo, tankMat)
    turret.position.y = 0.4
    singleBushing.add(turret)

    // 瓷套主绝缘体 (带伞裙级联)
    const stemGeo = new THREE.CylinderGeometry(0.2, 0.28, 3.6, 16)
    const stem = new THREE.Mesh(stemGeo, porcelainMat)
    stem.position.y = 2.4
    singleBushing.add(stem)

    // 伞裙 (Sheds)
    for (let s = 1.0; s <= 3.6; s += 0.4) {
      const shedGeo = new THREE.ConeGeometry(0.52 - s * 0.05, 0.18, 16)
      const shed = new THREE.Mesh(shedGeo, porcelainMat)
      shed.position.y = s + 0.6
      singleBushing.add(shed)
    }

    // 顶部接线端子与均压环 (Corona Ring & Terminal)
    const ringGeo = new THREE.TorusGeometry(0.48, 0.06, 8, 24)
    const ring = new THREE.Mesh(ringGeo, brassMat)
    ring.rotation.x = Math.PI / 2
    ring.position.y = 4.2
    singleBushing.add(ring)

    const capGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.6, 12)
    const cap = new THREE.Mesh(capGeo, brassMat)
    cap.position.y = 4.5
    singleBushing.add(cap)

    bushingGroup.add(singleBushing)
  })

  // 110kV/35kV 低压侧套管 (3基，较小较直)
  ;[-1.8, 0, 1.8].forEach((xPos) => {
    const lvBushing = new THREE.Group()
    lvBushing.position.set(xPos, 0.2, -1.3)

    const lvTurret = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.4, 0.6, 12), tankMat)
    lvTurret.position.y = 0.3
    lvBushing.add(lvTurret)

    const lvStem = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.22, 2.0, 12), porcelainMat)
    lvStem.position.y = 1.4
    lvBushing.add(lvStem)

    const lvCap = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.4, 12), brassMat)
    lvCap.position.y = 2.5
    lvBushing.add(lvCap)

    bushingGroup.add(lvBushing)
  })

  lidGroup.add(bushingGroup)
  root.add(lidGroup)
  explodableParts.tankLid = lidGroup
  explodableParts.bushings = bushingGroup

  // 5. 储油柜 (油枕) 与瓦斯继电器 (Conservator)
  const conservatorGroup = new THREE.Group()
  conservatorGroup.position.set(0, 9.5, -2.6)

  // 储油柜圆柱罐体
  const tankCylGeo = new THREE.CylinderGeometry(1.1, 1.1, 6.8, 20)
  const tankCyl = new THREE.Mesh(tankCylGeo, tankMat)
  tankCyl.rotation.z = Math.PI / 2
  conservatorGroup.add(tankCyl)

  // 两端封头
  ;[-3.4, 3.4].forEach((xPos) => {
    const cap = new THREE.Mesh(new THREE.SphereGeometry(1.1, 16, 16, 0, Math.PI * 2, 0, Math.PI / 2), tankMat)
    cap.rotation.z = xPos > 0 ? -Math.PI / 2 : Math.PI / 2
    cap.position.x = xPos
    conservatorGroup.add(cap)
  })

  // 油位指示计 (Oil Level Gauge)
  const gaugeGeo = new THREE.CylinderGeometry(0.15, 0.15, 1.2, 12)
  const gaugeMat = new THREE.MeshBasicMaterial({ color: 0x00f59b })
  const gauge = new THREE.Mesh(gaugeGeo, gaugeMat)
  gauge.position.set(3.5, 0, 0.8)
  conservatorGroup.add(gauge)

  // 连接主油箱管道与瓦斯继电器 (Buchholz Relay)
  const pipeGeo = new THREE.CylinderGeometry(0.15, 0.15, 2.2, 12)
  const pipe = new THREE.Mesh(pipeGeo, metalAccentMat)
  pipe.position.set(0, -1.2, 0.5)
  conservatorGroup.add(pipe)

  const relayGeo = new THREE.BoxGeometry(0.6, 0.6, 0.6)
  const relay = new THREE.Mesh(relayGeo, brassMat)
  relay.position.set(0, -1.2, 0.5)
  conservatorGroup.add(relay)

  root.add(conservatorGroup)
  explodableParts.conservator = conservatorGroup

  // 6. 左右两侧大型片式散热器组与风机 (Cooling Radiator Banks)
  const createRadiatorBank = (isLeft = true) => {
    const bankGroup = new THREE.Group()
    const xPos = isLeft ? -5.2 : 5.2
    bankGroup.position.set(xPos, 4.8, 0)

    // 上下集油总管
    const manifoldGeo = new THREE.CylinderGeometry(0.25, 0.25, 4.4, 12)
    manifoldGeo.rotateX(Math.PI / 2)
    const topManifold = new THREE.Mesh(manifoldGeo, tankMat)
    topManifold.position.y = 2.4
    bankGroup.add(topManifold)

    const btmManifold = new THREE.Mesh(manifoldGeo, tankMat)
    btmManifold.position.y = -2.4
    bankGroup.add(btmManifold)

    // 密集散热扁管组 (8片)
    const finGeo = new THREE.BoxGeometry(0.08, 4.6, 1.8)
    for (let z = -2.0; z <= 2.0; z += 0.55) {
      const fin = new THREE.Mesh(finGeo, metalAccentMat)
      fin.position.z = z
      bankGroup.add(fin)
    }

    // 底部散热风机 (2台)
    ;[-1.0, 1.0].forEach(zPos => {
      const fanGeo = new THREE.CylinderGeometry(0.6, 0.6, 0.4, 16)
      const fan = new THREE.Mesh(fanGeo, new THREE.MeshStandardMaterial({ color: 0x1f2937 }))
      fan.position.set(0, -2.8, zPos)
      bankGroup.add(fan)
    })

    return bankGroup
  }

  const radLeft = createRadiatorBank(true)
  const radRight = createRadiatorBank(false)
  root.add(radLeft)
  root.add(radRight)
  explodableParts.radiatorLeft = radLeft
  explodableParts.radiatorRight = radRight

  // 7. 红外热成像模式材质切换逻辑
  const originalMaterials = new Map()
  // 缓存原始材质
  root.traverse(child => {
    if (child.isMesh) {
      originalMaterials.set(child, child.material)
      child.userData.parentDevice = root
    }
  })

  // 热像渐变材质调色板 (蓝->绿->黄->橙->红)
  const thermalNormalMat = new THREE.MeshStandardMaterial({
    color: 0x00b4d8,
    roughness: 0.3,
    metalness: 0.2,
    emissive: 0x00457c,
    emissiveIntensity: 0.6
  })
  const thermalWarmMat = new THREE.MeshStandardMaterial({
    color: 0xffb703,
    roughness: 0.3,
    metalness: 0.2,
    emissive: 0xcc8500,
    emissiveIntensity: 0.7
  })
  const thermalHotMat = new THREE.MeshStandardMaterial({
    color: 0xff0055,
    roughness: 0.2,
    metalness: 0.2,
    emissive: 0xff0033,
    emissiveIntensity: 0.95
  })

  root.setThermalMode = function(enabled, isOverheat = false) {
    root.traverse(child => {
      if (child.isMesh) {
        if (!enabled) {
          child.material = originalMaterials.get(child)
        } else {
          // 在热力图模式下按部件位置分配热力色彩
          if (child.parent === explodableParts.coreAndWindings || child.parent === explodableParts.tankBody) {
            child.material = isOverheat ? thermalHotMat : thermalWarmMat
          } else {
            child.material = thermalNormalMat
          }
        }
      }
    })
  }

  // 8. 爆炸拆解动画控制 (Exploded View)
  let isExploded = false
  root.setExploded = function(exploded) {
    if (isExploded === exploded) return
    isExploded = exploded

    const duration = 1200
    // 箱盖上移
    new TWEEN.Tween(explodableParts.tankLid.position)
      .to({ y: exploded ? 13.5 : 7.8 }, duration)
      .easing(TWEEN.Easing.Cubic.Out)
      .start()

    // 油枕后移上抬
    new TWEEN.Tween(explodableParts.conservator.position)
      .to({ y: exploded ? 15.2 : 9.5, z: exploded ? -6.0 : -2.6 }, duration)
      .easing(TWEEN.Easing.Cubic.Out)
      .start()

    // 左右散热器向外推开
    new TWEEN.Tween(explodableParts.radiatorLeft.position)
      .to({ x: exploded ? -9.5 : -5.2 }, duration)
      .easing(TWEEN.Easing.Cubic.Out)
      .start()

    new TWEEN.Tween(explodableParts.radiatorRight.position)
      .to({ x: exploded ? 9.5 : 5.2 }, duration)
      .easing(TWEEN.Easing.Cubic.Out)
      .start()

    // 油箱箱体半透明前移或下沉
    new TWEEN.Tween(explodableParts.tankBody.position)
      .to({ z: exploded ? 5.5 : 0 }, duration)
      .easing(TWEEN.Easing.Cubic.Out)
      .start()

    // 内部线圈微微向上突出，便于清晰观察
    new TWEEN.Tween(explodableParts.coreAndWindings.position)
      .to({ y: exploded ? 5.8 : 4.8 }, duration)
      .easing(TWEEN.Easing.Cubic.Out)
      .start()
  }

  return root
}
