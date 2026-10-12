import * as THREE from 'three'

/**
 * 创建变电站站区基础设施 (地坪、道路、围栏、主控楼、灯塔、线槽)
 */
export function createEnvironment() {
  const group = new THREE.Group()
  group.name = 'Substation_Environment'

  // 1. 主地坪 (Dark Concrete Base with Sci-fi Grid)
  const groundGeo = new THREE.PlaneGeometry(220, 160)
  const groundMat = new THREE.MeshStandardMaterial({
    color: 0x0c1220,
    roughness: 0.85,
    metalness: 0.15,
  })
  const ground = new THREE.Mesh(groundGeo, groundMat)
  ground.rotation.x = -Math.PI / 2
  ground.receiveShadow = true
  group.add(ground)

  // 1.1 工业科技网格线 (Grid Helper overlay)
  const gridHelper = new THREE.GridHelper(220, 55, 0x00f0ff, 0x15294b)
  gridHelper.position.y = 0.05
  gridHelper.material.opacity = 0.35
  gridHelper.material.transparent = true
  group.add(gridHelper)

  // 2. 环形巡检道路 (Asphalt Road)
  const roadMat = new THREE.MeshStandardMaterial({
    color: 0x161d2d,
    roughness: 0.9,
    metalness: 0.1
  })
  const roadGeo = new THREE.PlaneGeometry(180, 10)
  
  // 南北向主干道
  const road1 = new THREE.Mesh(roadGeo, roadMat)
  road1.rotation.x = -Math.PI / 2
  road1.position.set(0, 0.08, 45)
  group.add(road1)

  const road2 = new THREE.Mesh(roadGeo, roadMat)
  road2.rotation.x = -Math.PI / 2
  road2.position.set(0, 0.08, -45)
  group.add(road2)

  // 东西向横向道路
  const roadCrossGeo = new THREE.PlaneGeometry(10, 100)
  const road3 = new THREE.Mesh(roadCrossGeo, roadMat)
  road3.rotation.x = -Math.PI / 2
  road3.position.set(-75, 0.08, 0)
  group.add(road3)

  const road4 = new THREE.Mesh(roadCrossGeo, roadMat)
  road4.rotation.x = -Math.PI / 2
  road4.position.set(75, 0.08, 0)
  group.add(road4)

  // 3. 黄黑安全斑马线 / 警示线边缘
  const stripeGeo = new THREE.BoxGeometry(180, 0.15, 0.6)
  const stripeMat = new THREE.MeshBasicMaterial({ color: 0xffb703 })
  const stripe1 = new THREE.Mesh(stripeGeo, stripeMat)
  stripe1.position.set(0, 0.1, 40)
  group.add(stripe1)
  const stripe2 = new THREE.Mesh(stripeGeo, stripeMat)
  stripe2.position.set(0, 0.1, -40)
  group.add(stripe2)

  // 4. 主控楼建筑 (Main Control Building)
  const buildingGroup = new THREE.Group()
  buildingGroup.position.set(-65, 0, 0)

  // 楼体本体 (2层现代工业风格)
  const bldgGeo = new THREE.BoxGeometry(20, 14, 40)
  const bldgMat = new THREE.MeshStandardMaterial({
    color: 0x1c2738,
    roughness: 0.6,
    metalness: 0.3
  })
  const bldg = new THREE.Mesh(bldgGeo, bldgMat)
  bldg.position.y = 7
  bldg.castShadow = true
  bldg.receiveShadow = true
  buildingGroup.add(bldg)

  // 楼顶配电女儿墙
  const roofGeo = new THREE.BoxGeometry(20.4, 0.8, 40.4)
  const roofMat = new THREE.MeshStandardMaterial({ color: 0x111a28, roughness: 0.5 })
  const roof = new THREE.Mesh(roofGeo, roofMat)
  roof.position.y = 14.4
  buildingGroup.add(roof)

  // 玻璃幕墙 / 窗户带发光
  const windowMat = new THREE.MeshBasicMaterial({
    color: 0x00f0ff,
    transparent: true,
    opacity: 0.75
  })
  // 窗条
  for (let i = 0; i < 4; i++) {
    const winGeo = new THREE.BoxGeometry(0.3, 2.2, 6)
    const win = new THREE.Mesh(winGeo, windowMat)
    win.position.set(10.1, 4 + (i % 2) * 5.5, -12 + Math.floor(i / 2) * 16)
    buildingGroup.add(win)
  }

  // 通信铁塔与天线
  const towerGeo = new THREE.CylinderGeometry(0.2, 0.8, 12, 6)
  const towerMat = new THREE.MeshStandardMaterial({ color: 0x8899aa, metalness: 0.7 })
  const tower = new THREE.Mesh(towerGeo, towerMat)
  tower.position.set(0, 20, -10)
  buildingGroup.add(tower)

  // 顶端航空障碍警示红灯
  const lightGeo = new THREE.SphereGeometry(0.35, 12, 12)
  const lightMat = new THREE.MeshBasicMaterial({ color: 0xff3344 })
  const redLight = new THREE.Mesh(lightGeo, lightMat)
  redLight.position.set(0, 26.2, -10)
  buildingGroup.add(redLight)

  group.add(buildingGroup)

  // 5. 四周工业安全防撞护栏
  const fenceMat = new THREE.MeshStandardMaterial({ color: 0x4a5568, metalness: 0.5, roughness: 0.5 })
  const createFenceLine = (start, end) => {
    const len = start.distanceTo(end)
    const lineGeo = new THREE.CylinderGeometry(0.08, 0.08, len, 8)
    const fence = new THREE.Mesh(lineGeo, fenceMat)
    const center = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5)
    fence.position.copy(center)
    fence.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), end.clone().sub(start).normalize())
    group.add(fence)
  }

  // 围栏立柱与横杆 (简炼工业感)
  for (let x = -85; x <= 85; x += 15) {
    const postGeo = new THREE.CylinderGeometry(0.12, 0.12, 2.2, 8)
    const postNorth = new THREE.Mesh(postGeo, fenceMat)
    postNorth.position.set(x, 1.1, -55)
    group.add(postNorth)

    const postSouth = new THREE.Mesh(postGeo, fenceMat)
    postSouth.position.set(x, 1.1, 55)
    group.add(postSouth)
  }

  // 6. 变电站高杆泛光照明灯塔 (4基)
  const lightTowerPos = [
    [-65, 40], [65, 40], [-65, -40], [65, -40]
  ]
  lightTowerPos.forEach(([tx, tz]) => {
    const towerMast = new THREE.Mesh(
      new THREE.CylinderGeometry(0.2, 0.45, 16, 8),
      new THREE.MeshStandardMaterial({ color: 0x5a6a7e, metalness: 0.8, roughness: 0.3 })
    )
    towerMast.position.set(tx, 8, tz)
    group.add(towerMast)

    // 灯盘
    const head = new THREE.Mesh(
      new THREE.CylinderGeometry(1.2, 1.2, 0.4, 8),
      new THREE.MeshStandardMaterial({ color: 0x223344 })
    )
    head.position.set(tx, 16, tz)
    group.add(head)

    // 发光灯泡
    const lamp = new THREE.Mesh(
      new THREE.SphereGeometry(0.6, 12, 12),
      new THREE.MeshBasicMaterial({ color: 0x00f0ff })
    )
    lamp.position.set(tx, 15.6, tz)
    group.add(lamp)
  })

  return group
}
