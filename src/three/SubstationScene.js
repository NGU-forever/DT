import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'
import TWEEN from '@tweenjs/tween.js'

import { createEnvironment } from './models/Environment.js'
import { createTransformer } from './models/Transformer.js'
import { createGISBay } from './models/GISBay.js'
import { createGantrySystem } from './models/Gantries.js'
import { FlowParticles } from './effects/FlowParticles.js'
import { AlarmRings } from './effects/AlarmRings.js'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/examples/jsm/loaders/DRACOLoader.js'

export class SubstationScene {
  constructor(container, onSelectDevice) {
    this.container = container
    this.onSelectDevice = onSelectDevice
    this.clock = new THREE.Clock()

    this.scene = null
    this.camera = null
    this.renderer = null
    this.controls = null
    this.composer = null

    this.devicesMap = new Map()
    this.raycaster = new THREE.Raycaster()
    this.mouse = new THREE.Vector2()

    this.flowParticles = null
    this.alarmRings = null

    this.isPatrolling = false
    this.patrolAngle = 0
    this.animationFrameId = null
    this.mixers = []
    this.loadedGltfGroup = null

    this.init()
  }

  init() {
    const width = this.container.clientWidth || window.innerWidth
    const height = this.container.clientHeight || window.innerHeight

    // 1. Scene
    this.scene = new THREE.Scene()
    this.scene.background = new THREE.Color(0x060a14)
    this.scene.fog = new THREE.FogExp2(0x060a14, 0.007)

    // 2. Camera
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.5, 500)
    this.camera.position.set(0, 55, 80)

    // 3. Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' })
    this.renderer.setSize(width, height)
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    this.renderer.shadowMap.enabled = true
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping
    this.renderer.toneMappingExposure = 1.15
    this.container.appendChild(this.renderer.domElement)

    // 4. Controls
    this.controls = new OrbitControls(this.camera, this.renderer.domElement)
    this.controls.enableDamping = true
    this.controls.dampingFactor = 0.05
    this.controls.maxPolarAngle = Math.PI / 2 - 0.05
    this.controls.minDistance = 8
    this.controls.maxDistance = 220
    this.controls.target.set(0, 5, 0)

    // 5. Lights
    this.setupLights()

    // 6. Post-processing (UnrealBloomPass)
    this.setupPostProcessing(width, height)

    // 7. Load Models
    this.setupModels()

    // 8. Visual Effects
    this.flowParticles = new FlowParticles(this.scene)
    this.alarmRings = new AlarmRings(this.scene)

    // 9. Events
    this.bindEvents()

    // 10. Start Loop
    this.animate()
  }

  setupLights() {
    const ambientLight = new THREE.AmbientLight(0x1a2638, 1.8)
    this.scene.add(ambientLight)

    const mainSun = new THREE.DirectionalLight(0xddeeff, 2.2)
    mainSun.position.set(60, 90, 50)
    mainSun.castShadow = true
    mainSun.shadow.mapSize.width = 2048
    mainSun.shadow.mapSize.height = 2048
    mainSun.shadow.camera.near = 10
    mainSun.shadow.camera.far = 250
    const d = 80
    mainSun.shadow.camera.left = -d
    mainSun.shadow.camera.right = d
    mainSun.shadow.camera.top = d
    mainSun.shadow.camera.bottom = -d
    this.scene.add(mainSun)

    // 科技蓝微补光
    const cyanLight = new THREE.DirectionalLight(0x00f0ff, 0.8)
    cyanLight.position.set(-60, 40, -40)
    this.scene.add(cyanLight)
  }

  setupPostProcessing(width, height) {
    const renderPass = new RenderPass(this.scene, this.camera)
    const bloomPass = new UnrealBloomPass(
      new THREE.Vector2(width, height),
      0.65, // strength
      0.4,  // radius
      0.82  // threshold
    )

    this.composer = new EffectComposer(this.renderer)
    this.composer.addPass(renderPass)
    this.composer.addPass(bloomPass)
  }

  setupModels() {
    // 站区环境
    const env = createEnvironment()
    this.scene.add(env)

    // 高压架构与母线
    const gantries = createGantrySystem()
    this.scene.add(gantries)

    // 1# 主变压器
    const trans1 = createTransformer('trans-1', new THREE.Vector3(-20, 0, 10), '1# 主变压器 (220kV)')
    this.scene.add(trans1)
    this.devicesMap.set('trans-1', trans1)

    // 2# 主变压器
    const trans2 = createTransformer('trans-2', new THREE.Vector3(20, 0, 10), '2# 主变压器 (220kV)')
    this.scene.add(trans2)
    this.devicesMap.set('trans-2', trans2)

    // 220kV GIS 201 进线断路器
    const gis201 = createGISBay('gis-201', new THREE.Vector3(-20, 0, -20), '220kV GIS 201 进线断路器')
    this.scene.add(gis201)
    this.devicesMap.set('gis-201', gis201)

    // 220kV GIS 202 母联断路器
    const gis202 = createGISBay('gis-202', new THREE.Vector3(0, 0, -20), '220kV GIS 202 母联断路器')
    this.scene.add(gis202)
    this.devicesMap.set('gis-202', gis202)

    // 110kV GIS 101 出线断路器
    const gis101 = createGISBay('gis-101', new THREE.Vector3(20, 0, -20), '110kV GIS 101 出线断路器')
    this.scene.add(gis101)
    this.devicesMap.set('gis-101', gis101)
  }

  bindEvents() {
    this.onWindowResize = this.onWindowResize.bind(this)
    this.onPointerDown = this.onPointerDown.bind(this)

    window.addEventListener('resize', this.onWindowResize)
    this.container.addEventListener('pointerdown', this.onPointerDown)
  }

  onWindowResize() {
    if (!this.container || !this.renderer) return
    const width = this.container.clientWidth
    const height = this.container.clientHeight

    this.camera.aspect = width / height
    this.camera.updateProjectionMatrix()
    this.renderer.setSize(width, height)
    this.composer.setSize(width, height)
  }

  onPointerDown(event) {
    const rect = this.container.getBoundingClientRect()
    this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
    this.mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1

    this.raycaster.setFromCamera(this.mouse, this.camera)
    const intersects = this.raycaster.intersectObjects(this.scene.children, true)

    if (intersects.length > 0) {
      let target = null
      for (const hit of intersects) {
        if (hit.object.userData && hit.object.userData.parentDevice) {
          target = hit.object.userData.parentDevice
          break
        } else if (hit.object.userData && hit.object.userData.isDevice) {
          target = hit.object
          break
        }
      }

      if (target && target.userData && target.userData.deviceId) {
        const deviceId = target.userData.deviceId
        if (this.onSelectDevice) {
          this.onSelectDevice(deviceId)
        }
      }
    }
  }

  // 视角运镜平滑过渡
  flyTo(targetPos, targetLookAt, duration = 1200) {
    this.isPatrolling = false

    new TWEEN.Tween(this.camera.position)
      .to(targetPos, duration)
      .easing(TWEEN.Easing.Cubic.Out)
      .start()

    new TWEEN.Tween(this.controls.target)
      .to(targetLookAt, duration)
      .easing(TWEEN.Easing.Cubic.Out)
      .start()
  }

  setCameraView(viewName) {
    if (viewName === 'overview') {
      this.flyTo({ x: 0, y: 55, z: 80 }, { x: 0, y: 5, z: 0 })
    } else if (viewName === 'transformer1') {
      this.flyTo({ x: -20, y: 16, z: 28 }, { x: -20, y: 5, z: 10 })
    } else if (viewName === 'transformer2') {
      this.flyTo({ x: 20, y: 16, z: 28 }, { x: 20, y: 5, z: 10 })
    } else if (viewName === 'gis') {
      this.flyTo({ x: 0, y: 14, z: -2 }, { x: 0, y: 4, z: -20 })
    } else if (viewName === 'patrol') {
      this.isPatrolling = true
    }
  }

  // 红外热成像模式联动
  setHeatmapMode(enabled, activeFault = null) {
    const t1 = this.devicesMap.get('trans-1')
    const t2 = this.devicesMap.get('trans-2')
    if (t1) t1.setThermalMode(enabled, activeFault === 'trans_overheat')
    if (t2) t2.setThermalMode(enabled, false)
  }

  // 设备部件爆炸拆解模式联动
  setExplodedView(exploded) {
    const t1 = this.devicesMap.get('trans-1')
    const t2 = this.devicesMap.get('trans-2')
    if (t1) t1.setExploded(exploded)
    if (t2) t2.setExploded(exploded)
  }

  // 断路器开关状态联动
  updateBreakerState(deviceId, isClosed) {
    const dev = this.devicesMap.get(deviceId)
    if (dev && dev.setBreakerState) {
      dev.setBreakerState(isClosed)
    }

    if (deviceId === 'gis-201') {
      this.flowParticles.setLineActive('gis', isClosed)
    } else if (deviceId === 'gis-101') {
      this.flowParticles.setLineActive('out', isClosed)
    }
  }

  // 告警联动处理
  handleFaultTrigger(faultType) {
    this.alarmRings.clearAll()

    if (faultType === 'trans_overheat') {
      this.alarmRings.addAlarm('trans-1', new THREE.Vector3(-20, 0, 10), 0xff0044)
      this.setCameraView('transformer1')
      this.setHeatmapMode(true, 'trans_overheat')
    } else if (faultType === 'sf6_leak') {
      this.alarmRings.addAlarm('gis-201', new THREE.Vector3(-20, 0, -20), 0xffaa00)
      this.setCameraView('gis')
    } else if (faultType === 'overload_trip') {
      this.alarmRings.addAlarm('gis-101', new THREE.Vector3(20, 0, -20), 0xff0044)
      this.setCameraView('gis')
      this.updateBreakerState('gis-101', false)
    } else {
      this.setHeatmapMode(false)
    }
  }

  clearFault() {
    this.alarmRings.clearAll()
    this.setHeatmapMode(false)
    this.updateBreakerState('gis-201', true)
    this.updateBreakerState('gis-101', true)
  }

  // 加载外部 Blender 导出的 GLTF / GLB 模型
  loadGLTFModel(urlOrBuffer, onProgress) {
    return new Promise((resolve, reject) => {
      const loader = new GLTFLoader()
      const dracoLoader = new DRACOLoader()
      dracoLoader.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.7/')
      loader.setDRACOLoader(dracoLoader)

      const onLoad = (gltf) => {
        if (this.loadedGltfGroup) {
          this.scene.remove(this.loadedGltfGroup)
        }
        const model = gltf.scene
        this.loadedGltfGroup = model
        model.name = 'Blender_Imported_Model'

        // 遍历设置阴影与设备识别
        model.traverse((child) => {
          if (child.isMesh) {
            child.castShadow = true
            child.receiveShadow = true
            child.userData.isDevice = true
            child.userData.deviceId = child.name || 'blender-device'
            child.userData.name = child.name || 'Blender 导入部件'
            child.userData.parentDevice = child
          }
        })

        // 处理 Blender 关键帧/变形动画
        if (gltf.animations && gltf.animations.length > 0) {
          const mixer = new THREE.AnimationMixer(model)
          gltf.animations.forEach((clip) => {
            mixer.clipAction(clip).play()
          })
          this.mixers.push(mixer)
        }

        // 调整模型至场景中央适宜比例
        const box = new THREE.Box3().setFromObject(model)
        const size = box.getSize(new THREE.Vector3())
        const center = box.getCenter(new THREE.Vector3())

        model.position.x += model.position.x - center.x
        model.position.y += -box.min.y
        model.position.z += model.position.z - center.z

        this.scene.add(model)
        resolve(gltf)
      }

      if (typeof urlOrBuffer === 'string') {
        loader.load(urlOrBuffer, onLoad, onProgress, reject)
      } else {
        loader.parse(urlOrBuffer, '', onLoad, reject)
      }
    })
  }

  animate() {
    this.animationFrameId = requestAnimationFrame(this.animate.bind(this))

    const delta = this.clock.getDelta()
    TWEEN.update()

    // 更新 Blender 导入的骨骼/关键帧动画
    this.mixers.forEach(m => m.update(delta))

    // 自动巡航漫游逻辑
    if (this.isPatrolling) {
      this.patrolAngle += delta * 0.2
      const radius = 80
      this.camera.position.x = Math.sin(this.patrolAngle) * radius
      this.camera.position.z = Math.cos(this.patrolAngle) * radius
      this.camera.position.y = 42 + Math.sin(this.patrolAngle * 2) * 8
      this.controls.target.set(0, 5, 0)
    }

    this.controls.update()

    // 更新粒子流与告警光环
    if (this.flowParticles) {
      this.flowParticles.update(delta)
    }
    if (this.alarmRings) {
      this.alarmRings.update(delta)
    }

    if (this.composer) {
      this.composer.render()
    } else {
      this.renderer.render(this.scene, this.camera)
    }
  }

  destroy() {
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId)
    }
    window.removeEventListener('resize', this.onWindowResize)
    if (this.container && this.renderer && this.renderer.domElement) {
      this.container.removeChild(this.renderer.domElement)
    }
    if (this.renderer) {
      this.renderer.dispose()
    }
  }
}
