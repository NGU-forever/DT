import * as THREE from 'three'

/**
 * 创建 220kV GIS 组合电器设备间隔模型 (Gas Insulated Switchgear)
 * @param {string} deviceId 设备标识 (如 'gis-201', 'gis-202')
 * @param {THREE.Vector3} position 坐标位置
 * @param {string} label 设备名称
 */
export function createGISBay(deviceId, position, label = '220kV GIS 断路器') {
  const root = new THREE.Group()
  root.position.copy(position)
  root.name = deviceId

  // 可交互设备元数据
  root.userData = {
    isDevice: true,
    deviceId: deviceId,
    name: label,
    type: 'gis'
  }

  // 材质体系
  const metalBodyMat = new THREE.MeshStandardMaterial({
    color: 0x8291a5, // 银灰镀锌/铝合金GIS壳体
    roughness: 0.35,
    metalness: 0.8,
  })
  const steelFrameMat = new THREE.MeshStandardMaterial({
    color: 0x3d4756,
    roughness: 0.6,
    metalness: 0.6,
  })
  const flangeMat = new THREE.MeshStandardMaterial({
    color: 0x5a6575,
    roughness: 0.4,
    metalness: 0.7,
  })
  const gaugeFaceMat = new THREE.MeshBasicMaterial({ color: 0x00f59b })
  const stateLedRedMat = new THREE.MeshBasicMaterial({ color: 0xff3344 }) // 合闸 (红)
  const stateLedGreenMat = new THREE.MeshBasicMaterial({ color: 0x00f59b }) // 分闸 (绿)

  // 1. 钢结构支撑底座 (Structural Support Legs)
  const legGeo = new THREE.BoxGeometry(0.35, 3.2, 0.35)
  ;[-2.4, 2.4].forEach(x => {
    ;[-1.5, 1.5].forEach(z => {
      const leg = new THREE.Mesh(legGeo, steelFrameMat)
      leg.position.set(x, 1.6, z)
      leg.castShadow = true
      root.add(leg)
    })
  })

  // 水平支撑槽钢
  const beamX = new THREE.Mesh(new THREE.BoxGeometry(5.2, 0.3, 0.35), steelFrameMat)
  beamX.position.set(0, 3.1, 0)
  root.add(beamX)

  // 2. 核心断路器气室筒体 (Circuit Breaker Pressure Cylinder)
  const breakerGroup = new THREE.Group()
  breakerGroup.position.set(0, 4.4, 0)

  // 主断路器卧式圆柱罐体
  const mainTankGeo = new THREE.CylinderGeometry(0.9, 0.9, 6.2, 24)
  mainTankGeo.rotateZ(Math.PI / 2)
  const mainTank = new THREE.Mesh(mainTankGeo, metalBodyMat)
  mainTank.castShadow = true
  breakerGroup.add(mainTank)

  // 连接法兰圈 (Flanges)
  ;[-2.8, -1.2, 1.2, 2.8].forEach(x => {
    const flangeGeo = new THREE.CylinderGeometry(1.02, 1.02, 0.22, 24)
    flangeGeo.rotateZ(Math.PI / 2)
    const flange = new THREE.Mesh(flangeGeo, flangeMat)
    flange.position.x = x
    breakerGroup.add(flange)
  })

  // 3. 上部隔离开关与出线母线引出套管 (3相垂直立柱气室)
  ;[-1.8, 0, 1.8].forEach(x => {
    // 垂直支管
    const vertCyl = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 2.4, 16), metalBodyMat)
    vertCyl.position.set(x, 1.8, 0)
    breakerGroup.add(vertCyl)

    // 拐角弯头 (Elbow)
    const elbow = new THREE.Mesh(new THREE.SphereGeometry(0.65, 16, 16), metalBodyMat)
    elbow.position.set(x, 3.0, 0)
    breakerGroup.add(elbow)

    // 橫向母线连接筒
    const busDuct = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 3.0, 16), metalBodyMat)
    busDuct.rotation.x = Math.PI / 2
    busDuct.position.set(x, 3.0, -1.5)
    breakerGroup.add(busDuct)

    // 避雷器小罐 (Surge Arrester)
    const arrester = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.28, 1.4, 12), metalBodyMat)
    arrester.position.set(x, 4.0, 0)
    breakerGroup.add(arrester)
  })

  // 4. 弹簧操动机构箱 (Spring Mechanism Cubicle)
  const cubicleGeo = new THREE.BoxGeometry(1.6, 2.2, 1.2)
  const cubicleMat = new THREE.MeshStandardMaterial({ color: 0x222d3d, roughness: 0.5 })
  const cubicle = new THREE.Mesh(cubicleGeo, cubicleMat)
  cubicle.position.set(0, -1.2, 1.4)
  breakerGroup.add(cubicle)

  // SF6 气体压力密度表 (Density Gauge)
  const gaugeGeo = new THREE.CylinderGeometry(0.22, 0.22, 0.1, 16)
  gaugeGeo.rotateX(Math.PI / 2)
  const gauge = new THREE.Mesh(gaugeGeo, gaugeFaceMat)
  gauge.position.set(-0.4, -0.6, 2.05)
  breakerGroup.add(gauge)

  // 断路器分合闸状态指示灯 (合闸红灯 / 分闸绿灯)
  const ledGeo = new THREE.SphereGeometry(0.12, 12, 12)
  const stateLed = new THREE.Mesh(ledGeo, stateLedRedMat)
  stateLed.position.set(0.4, -0.6, 2.05)
  breakerGroup.add(stateLed)

  root.add(breakerGroup)

  // 外部方法：更新断路器合分闸指示状态
  root.setBreakerState = function(isClosed) {
    stateLed.material = isClosed ? stateLedRedMat : stateLedGreenMat
  }

  // 挂载射线检测父指针
  root.traverse(child => {
    if (child.isMesh) {
      child.userData.parentDevice = root
    }
  })

  return root
}
