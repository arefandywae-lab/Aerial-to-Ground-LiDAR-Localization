# VPS บน LiDAR SLAM Map — Project Spec (Sim ล้วน)

สถานะ: draft · ทำใน Gazebo ทั้งหมด ไม่ใช้ sensor จริง · เครื่องพัฒนา: RTX 4060 Ti 8GB
**โจทย์หลักของโปรเจกต์ (headline):** โดรนมี LiDAR สร้าง map · ground robot มีแค่กล้อง localize ใน map นั้น · พื้นที่ urban เปิด (ถนน อาคาร ตรอก ซอย) ดูหัวข้อ 5b การทดลองใน room (หัวข้อ 1–5) เป็นฐานและ baseline ของโจทย์นี้
เงื่อนไข: method ที่ implement ใช้เทคโนโลยีปี 2025 หรือก่อนหน้า ส่วนงานปี 2026 ใช้ได้ในฐานะแหล่ง "แนวคิดและวิธีแก้ปัญหา" เท่านั้น (เขียน implementation เอง ไม่ยึดตัวงานหรือโค้ดของเขา)

---

## 1. โจทย์ปัญหา (Problem Statement)

LiDAR SLAM สร้าง map ที่แม่นเรขาคณิตและไม่ขึ้นกับแสง แต่ LiDAR ที่แม่นมีราคาแพง ขณะที่กล้องถูกและมีทุกอุปกรณ์ **VPS (Visual Positioning System)** คือการให้กล้องอย่างเดียว localize ตัวเองใน map ที่สร้างไว้ล่วงหน้า โปรเจกต์นี้ศึกษาการต่อกันของสองส่วน: **map จาก LiDAR SLAM → การ localize ด้วยกล้องล้วน**

ความยากหลักคือ modality gap: keypoint ฝั่งภาพอิงเท็กซ์เจอร์ แต่ฝั่ง point cloud อิงรูปทรง จึงหา keypoint ที่ซ้ำกันได้ยาก และงานที่ครบทั้ง place recognition กับ pose estimation ยังมีน้อย ส่วนใหญ่ทำแค่ cross-modal place recognition

นี่เป็นสาขาที่มีงานอยู่แล้ว (ดู 8) โปรเจกต์นี้**ไม่อ้างว่าเป็นคนแรก**

**คำถามวิจัย:**
- RQ1: กล้องล้วน localize ใน map ที่ FAST-LIO2 สร้างได้แม่นแค่ไหน (global localization จากศูนย์)
- RQ2: ความแม่นเปลี่ยนอย่างไรเมื่อสภาพภาพเปลี่ยน (แสง, มุมมอง, เท็กซ์เจอร์, วัตถุที่เปลี่ยนไป)
- RQ3: คุณภาพของ map (drift, noise, density) ส่งผลต่อ VPS แค่ไหน
- RQ4: ตำแหน่งจาก VPS ช่วยจำกัด drift ของ LIO ได้ไหม

**ขอบเขต (in scope):** sim ล้วน (Gazebo) พร้อม GT pose · กล้องเดียว (monocular) เป็น query · ระบบ LiDAR-inertial ที่ใช้คือ FAST-LIO2

**นอกขอบเขต (out of scope):** ข้อมูลจริงทุกชนิด · การ reproduce ตัวงานปี 2026 ทั้งชุด (ยืมเฉพาะแนวคิด) · การเทรนโมเดลขนาดใหญ่ · multi-robot

---

## 2. ข้อจำกัดของเครื่อง (8GB VRAM)

| เรื่อง | ข้อสรุป |
| --- | --- |
| Simulator | Gazebo Harmonic (GPU LiDAR + camera) เป็นตัวหลัก ประเมินว่าเบาพอสำหรับเครื่องนี้ ต้องวัดจริงในการทดลอง 9 |
| Isaac Sim | ตัดทิ้ง เปิดฉากเปล่าก็กิน VRAM เกือบหมด |
| Method แบบ learned / 3DGS | เป็นตัวเลือกเสริม รันได้ต่อเมื่อวัด VRAM แล้วไม่เกิน 8GB ยังไม่ได้เช็คของแต่ละตัว |
| กฎการใช้งาน | ห้ามรัน simulator พร้อมการเทรนหรือรัน method ที่กิน VRAM สูง ให้ปิด Gazebo ก่อน |

---

## 3. เครื่องมือที่จะสร้าง (Components)

| # | Component | หน้าที่ | Stack | Output |
| --- | --- | --- | --- | --- |
| 1 | Gazebo worlds + robot | หลาย world ปรับแสง/เท็กซ์เจอร์/วัตถุได้ หุ่นติด LiDAR + IMU + กล้อง publish GT pose วิ่งตาม trajectory ที่กำหนด | Gazebo Harmonic, ROS2, SDF | ข้อมูลดิบ + GT ต่อ session |
| 2 | Mapping node | รัน FAST-LIO2 สร้าง LiDAR map (และเวอร์ชัน colorized ด้วยสีจากกล้อง) | FAST-LIO2, ROS2, PCL | map (PCD) + estimated trajectory |
| 3 | Map degradation + confidence tool | ใส่ drift, noise, downsampling ที่ควบคุมได้ลงใน map และคำนวณ confidence ต่อ voxel จากสัญญาณที่หาได้ (เช่น ความหนาแน่น, ระดับ degeneracy ของ LIO) แนวคิดจากงาน LIO ปี 2026 ที่ปรับการอัปเดต voxel ตามความมั่นใจ (arXiv 2604.15864) | Python, Open3D | map หลายระดับคุณภาพ + แผนที่ confidence |
| 4 | VPS method wrapper | interface เดียว (ภาพ query → pose) ครอบทุก method ในหัวข้อ 4 | Python, PyTorch, OpenCV | pose ต่อ query + เวลา + VRAM |
| 5 | Evaluation harness | เทียบกับ GT คำนวณ recall ตาม threshold, error มัธยฐาน, success rate แยกตามเงื่อนไข พล็อตผล | Python, NumPy, Matplotlib | metrics + figures |
| 6 | VPS-aided pose graph | รวม odometry ของ LIO กับ pose fix จาก VPS เป็นระยะ ใน pose graph ถ่วงน้ำหนัก fix ตาม map confidence ได้ และมีโหมด loop closure ด้วย descriptor ของ LiDAR เป็นตัวเทียบ (แนวคิดจาก ISTD-LIOM ปี 2026) | GTSAM (หรือ g2o), ROS2 | trajectory ที่แก้ drift + ATE |

---

## 4. Method ที่จะเทียบ (M0, M2–M4 ใช้เทคโนโลยีปี 2025 หรือก่อนหน้า · M1 ยืมแนวคิดจากงานปี 2026)

| ID | Method | แนวคิด | หมายเหตุ |
| --- | --- | --- | --- |
| M0 | Visual-only reference | Hierarchical localization: global retrieval → local feature matching → 2D-3D → PnP บน map ที่สร้างจาก SfM ของภาพซิม | เป็นเพดานอ้างอิงที่ใช้ modality เดียวกัน |
| M1 | Map-as-images with provenance | render ภาพจาก LiDAR map จากหลาย virtual viewpoint แบบ offline และเก็บ 3D point ต่อ pixel ใช้ feature extractor/matcher ตัวเดียวกันกับภาพกล้องและภาพ render (ไม่ต้องเทรนข้าม modality) แล้วกู้ pose แบบ metric ด้วย PnP จาก 3D ที่เก็บไว้ | ยืมแนวคิดจากงานปี 2026 (arXiv 2609.27363) เขียนเอง งานต้นฉบับใช้ reflectivity ส่วนเราใช้ depth/normal/สี (ถ้า map colorized) เป็นค่าตั้งต้น เพราะยังไม่ได้ตรวจ intensity ของ Gazebo |
| M2 | Learned image-to-point-cloud | CMR-Agent / LHMap-loc | เสริม ขึ้นกับว่ามีโค้ด/weights และ VRAM พอ |
| M3 | Gaussian-splatting map | แบบ 3DGS-ReLoc: เริ่มเทรน Gaussian map จาก LiDAR, render, จับคู่ภาพ แล้ว PnP | เสริม ฉากเล็กเท่านั้นเพราะ VRAM |
| M4 | Visual regression reference | R-SCoRe (scene coordinate regression) | เสริม ใช้เป็น baseline ภาพล้วนระดับ SOTA ปี 2025 |

M0 และ M1 คือแกนหลัก เพราะ implement เองได้และควบคุมได้ M2–M4 ทำเมื่อเวลาและ VRAM เอื้อ

---

## 5. การทดลอง (Experiments)

แต่ละการทดลองตอบหนึ่งคำถาม เปลี่ยนตัวแปรทีละตัว วัดเทียบ GT ของ Gazebo

| # | Experiment | คำถามที่ตอบ | ตัวแปรที่เปลี่ยน | Metric |
| --- | --- | --- | --- | --- |
| 1 | คุณภาพ map ตั้งต้น | FAST-LIO2 ใน sim drift เท่าไร map หนาแน่นแค่ไหน | world, ความเร็ว, ความยาวเส้นทาง | ATE, RPE (m, % ของระยะทาง), จำนวนจุดต่อ m³ |
| 2 | VPS ในสภาพปกติ (RQ1) | แต่ละ method localize ได้แม่นแค่ไหนเมื่อสภาพตรงกับตอนทำ map | method (M0, M1 + เสริม M2–M4) | recall ที่ threshold ตั้งต้น, error มัธยฐาน |
| 3 | แสงและ appearance (RQ2) | LiDAR map ช่วยให้ทนต่อแสงเปลี่ยนมากกว่า map ภาพไหม | แสง/เงา/เวลา ตอน query vs ตอนทำ map | recall แยกตามระดับแสง |
| 4 | Viewpoint offset (RQ2) | query ที่เส้นทางต่างจากตอนทำ map ได้ผลอย่างไร | offset ข้าง/สูง/yaw | recall เทียบขนาด offset |
| 5 | เท็กซ์เจอร์ vs โครงสร้าง (RQ2) | ฉากไหนที่ภาพล้มและฉากไหนที่เรขาคณิตล้ม | world: เท็กซ์เจอร์ต่ำ, โครงสร้างซ้ำ (ทางเดินยาว), ปกติ | recall แยกต่อ world |
| 6 | คุณภาพ map (RQ3) | map ที่เพี้ยนส่งผลต่อ VPS เท่าไร และ confidence ของ map ต่อบริเวณทำนายว่า VPS จะพังตรงไหนได้ไหม | drift, noise, downsampling, map geometry-only vs colorized | error vs ระดับความเพี้ยน, ความสัมพันธ์ระหว่าง confidence กับ error |
| 7 | map ล้าสมัย (RQ2) | วัตถุที่ย้ายหรือหายหลังทำ map ทำให้พังแค่ไหน | สัดส่วนฉากที่เปลี่ยน | recall เทียบสัดส่วนที่เปลี่ยน |
| 8 | VPS ช่วยจำกัด drift (RQ4) | pose fix เป็นระยะลด drift ของ LIO ได้เท่าไร ถ่วงน้ำหนักด้วย map confidence ช่วยไหม และเทียบกับ loop closure ของ LiDAR เป็นอย่างไร | ความถี่ fix, คุณภาพ fix, น้ำหนักเท่ากัน vs ถ่วงตาม confidence, โหมด: LIO ล้วน / +loop closure / +VPS / ทั้งคู่ | ATE เทียบกับ LIO ล้วน |
| 9 | Compute | รันบน 4060 Ti 8GB ได้ไหม | method, ขนาด map, ความละเอียดภาพ | latency ต่อ query (ms), peak VRAM (GB), เวลาเตรียม map |

### โปรโตคอลกลาง
- query set ชุดเดียวกันทุก method ในแต่ละการทดลอง
- ตั้งนิยาม "success" (threshold ของ translation/rotation) ก่อนเริ่ม ค่าตั้งต้นให้อิงธรรมเนียม benchmark การ localize ด้วยภาพ แล้วล็อกไว้ใช้ทุกการทดลอง ค่าที่แน่นอนยืนยันหลังได้ผลการทดลอง 1
- ถ้ามีส่วนที่ต้องเทรน แยก world เทรนกับ world ทดสอบตั้งแต่แรก
- fix random seed รันซ้ำหลายรอบ รายงานค่าเฉลี่ยพร้อม spread
- ใช้ GT จาก Gazebo ตัวเดียวกันทุกการทดลอง

### ข้อจำกัดที่ต้องระบุในรายงาน
ผลทั้งหมดมาจากซิม กล้องของ Gazebo ไม่สมจริงเท่าภาพจริง และยังไม่ได้ตรวจว่า LiDAR intensity ของ Gazebo สมจริงแค่ไหน ค่าตั้งต้นจึงไม่พึ่ง intensity (ใช้ depth/normal/สี) และ method ที่พึ่ง intensity texture จะประเมินอย่างเป็นธรรมไม่ได้จนกว่าจะตรวจ ผลจึงอ้างได้เฉพาะ "ในสภาพแวดล้อมจำลอง" การทดลอง 3, 5, 7 ที่เปลี่ยนสภาพแวดล้อมอย่างเป็นระบบคือส่วนที่ช่วยลดช่องว่างนี้

---

## 5b. ชุดทดลอง B: Aerial map → Ground query (เมืองเปิด)

สถานการณ์: **โดรน** (LiDAR + กล้อง) บินสำรวจแล้วสร้าง map · **ground robot** มีกล้องอย่างเดียว localize ใน map นั้น · พื้นที่ urban เปิด 200×200 ม. (ถนน, ตึกหลายความสูง, ตรอก/ซอย) · ยังเป็น sim ล้วน ใช้ M0/M1 (+LoFTR) เดิมเป็น baseline

**ความเสี่ยงหลัก:** มุมมองไม่ตรงกัน โดรนเห็นหลังคา/พื้น/ยอดสิ่งกีดขวาง แต่ ground เห็น facade ใต้ชายคา และในตรอก ซึ่ง map อาจไม่ครอบคลุม

**สิ่งที่ต้องสร้างเพิ่ม**
| # | งาน | หมายเหตุ |
| --- | --- | --- |
| B-a | Urban world generator ขนาด 200×200 ม. | ตึกหลายความสูง facade มี texture แบบหน้าต่างซ้ำ ตรอกแคบ ถนน ปรับ seed ได้ ต้องวัด VRAM/real-time factor ของ Gazebo ก่อนล็อกความหนาแน่นของตึก |
| B-b | โดรน (LiDAR + กล้อง + IMU + GT) | บินตามเส้นทาง lawnmower ที่ความสูงหลายระดับ (เช่น 30 และ 50 ม.) กล้องเอียงลงได้ |
| B-c | ground robot (กล้อง + GT) | วิ่งบนถนน/ตรอก กล้องสูง ~1.5 ม. เป็นชุด query |
| B-d | Virtual viewpoint แบบ ground | ใน M1 สุ่มจุด render ระดับพื้นถนนในที่ว่างของ map หลายทิศ (ไม่ใช้ท่าของโดรนเป็นจุด render) |
| B-e | Coverage metric | สัดส่วนผิว GT ระดับพื้น (facade, ถนน) ที่ map ครอบคลุม ใช้อธิบายว่าทำไม method ล้ม |

**การทดลอง**
| # | คำถาม | ตัวแปร | Metric |
| --- | --- | --- | --- |
| B1 | Map จากโดรนครอบคลุมสิ่งที่ ground เห็นแค่ไหน | ความสูงบิน, มุมกล้อง/LiDAR, เส้นทาง | ATE ของ LIO, coverage ของ facade/ตรอก |
| B2 | Cross-view localization (แกน) | method: M0 (ภาพโดรน) vs M1 (LiDAR+สีโดรน) vs M1+LoFTR | recall ตาม threshold, error มัธยฐาน, แยก query ถนนเปิด/ตรอก |
| B3 | ช่องว่างมุมมอง | ความสูงบิน, มุมกล้องโดรน, ความสูงกล้อง ground | recall เทียบมุม/ความสูง |
| B4 | โครงสร้างซ้ำในเมือง | facade ซ้ำ, ถนนตรงยาว, texture ต่ำ | recall แยกต่อ world |
| B5 | Compute บน 8GB | ขนาด map, จำนวน render, matcher | latency, peak VRAM, เวลาเตรียม map, RTF ของ Gazebo |

หมายเหตุ: สีของ map มาจากกล้องโดรน จึงไม่มีสีที่ facade ที่โดรนไม่เคยเห็น (ใช้อธิบายผล B2) ถ้า M3 (Gaussian) ถูกเพิ่มมาจะมีข้อจำกัดเดียวกัน

---

## 6. Deliverables

1. Repo ที่รันซ้ำได้: worlds, mapping, degradation tool, VPS wrapper, evaluation harness, pose graph
2. ตารางผลการทดลอง 9 ข้อ พร้อมกราฟ recall และ error
3. รายงานสั้นสรุป: โจทย์, วิธี, ผล, ข้อจำกัด

---

## 7. ความเสี่ยงและทางออก

| ความเสี่ยง | ทางออก |
| --- | --- |
| ช่องว่างระหว่างซิมกับของจริง (กล้อง, intensity) | จำกัดคำกล่าวอ้างให้ตรงกับที่วัด สุ่มเปลี่ยนแสง/เท็กซ์เจอร์ในการทดลอง 3, 5, 7 |
| Method ตัวเสริม (M2–M4) ไม่มีโค้ดหรือ VRAM ไม่พอ | แกนหลักคือ M0 และ M1 ที่ implement เองได้ ตัวเสริมทำเมื่อพร้อมเท่านั้น |
| LIO ใน Gazebo drift เองจนกระทบผล | วัดในการทดลอง 1 ก่อน และประเมิน VPS เทียบ GT ตรง ไม่พึ่ง odometry |
| Contribution ซ้ำกับงานที่มีอยู่ (เช่น งาน visual-inertial localization กับ prior LiDAR map และงาน 2D-3D line correspondence ที่จำกัด drift ของ visual odometry มีอยู่แล้ว) | อ่านงานที่ใกล้ที่สุดฉบับเต็มก่อนเริ่ม ปรับ contribution ให้เหลือเฉพาะส่วนที่ยืนยันแล้วว่ายังไม่มีคนทำ |
| แนวคิดจากงานปี 2026 อ่านจาก abstract/snippet เท่านั้น อาจตีความผิด | อ่านฉบับเต็มก่อน implement ส่วนที่ยืมแนวคิด และระบุในรายงานว่าส่วนไหนยืมมา |
| ขอบเขตกว้างเกินไป | ล็อก M0 + M1 และการทดลอง 1, 2, 3, 6, 8, 9 เป็นแกน การทดลอง 4, 5, 7 และ M2–M4 เป็นส่วนเสริม |

### Contribution ที่ตั้งใจ (สมมติฐาน ยังไม่ได้ตรวจว่าไม่มีใครทำ)
1. การศึกษาแบบควบคุมตัวแปรของผลกระทบจากคุณภาพ map ที่ LIO สร้างต่อความแม่นของ VPS และการดูว่า confidence ของ map ทำนายจุดที่ VPS พังได้ไหม (การทดลอง 6)
2. การเทียบ LiDAR map กับ map ภาพภายใต้การเปลี่ยนแสงและโครงสร้างอย่างเป็นระบบ บน GT ที่แม่นจากซิม (การทดลอง 3, 5)
3. การวิเคราะห์ว่า pose fix จาก VPS จำกัด drift ของ LIO ได้เท่าไรเมื่อเทียบกับความถี่และคุณภาพของ fix ผลของการถ่วงน้ำหนักด้วย map confidence และการเทียบกับ loop closure ของ LiDAR (การทดลอง 8)
4. Harness ที่รันซ้ำได้ครบในที่เดียว

---

## 8. งานที่เกี่ยวข้อง (ตรวจจาก abstract/snippet ยังไม่ได้อ่านฉบับเต็ม)

- Survey on Monocular Re-Localization (2023): การ localize กล้องใน LiDAR map เป็นเทรนด์ใหม่
- Cross-Modal Visual Relocalization in Prior LiDAR Maps Utilizing Intensity Textures (2024): ชี้ว่าโซลูชันครบวงจรมีน้อย ส่วนใหญ่ทำแค่ place recognition
- Monocular Visual Place Recognition in LiDAR Maps via Cross-Modal State Space Model (2024)
- CMR-Agent (2024): image-to-point-cloud registration แบบวนซ้ำ
- LHMap-loc (2024): monocular localization ด้วย LiDAR point cloud heat map
- End-to-end 2D-3D Registration between Image and LiDAR Point Cloud (2023)
- 3DGS-ReLoc (2024): Gaussian map จาก LiDAR + กล้อง สำหรับ visual relocalization
- Gaussian-LIC2 (2025): LiDAR-inertial-camera Gaussian splatting SLAM
- R-SCoRe (CVPR 2025) และ Reloc3r (2024): visual localization แบบ regression
- Visual Localization in 3D Maps: Comparing Point Cloud, Mesh, and NeRF Representations (2024)
- Visual-Inertial Localization With Prior LiDAR Map Constraints (2019): ใช้ prior LiDAR map จำกัด drift ของ visual-inertial odometry
- Monocular Camera Localization in Prior LiDAR Maps with 2D-3D Line Correspondences (2020): ลด drift และ pose jump ของ VO ด้วย line correspondence

### แหล่งแนวคิดปี 2026 (ยืมแนวคิด ไม่ใช้ตัวงาน)
- From LiDAR Maps to Visual Localization (arXiv 2609.27363): ทำให้ LiDAR map "ค้นด้วยภาพได้" ด้วยการ render เป็น quasi-image ที่เก็บ 2D-3D provenance แล้วใช้ visual feature/matcher ร่วมกับภาพกล้อง → ใช้กับ M1
- Environment-Adaptive Solid-State LiDAR-Inertial Odometry (arXiv 2604.15864): ปรับการอัปเดต voxel ตามความมั่นใจ ป้องกันการวัดคุณภาพต่ำทำลาย global map → ใช้กับ map confidence ในการทดลอง 6, 8
- ISTD-LIOM (IJRA, มีนาคม 2026): แก้ drift ของ LIO ด้วยฐานข้อมูล descriptor บน front end ของ FAST-LIO2 → ใช้เป็นตัวเทียบ loop closure ในการทดลอง 8
- FAST-LIO2 (2021): LiDAR-inertial odometry ที่ใช้สร้าง map

### อ้างอิง
- FAST-LIO2 — https://arxiv.org/abs/2107.06829
- Survey on Monocular Re-Localization — https://arxiv.org/abs/2311.15643
- Cross-Modal Visual Relocalization in Prior LiDAR Maps Utilizing Intensity Textures — https://arxiv.org/abs/2412.01299
- Monocular VPR in LiDAR Maps via Cross-Modal State Space Model — https://arxiv.org/abs/2410.06285
- CMR-Agent — https://arxiv.org/abs/2408.02394
- LHMap-loc — https://arxiv.org/abs/2403.05002
- End-to-end 2D-3D Registration between Image and LiDAR Point Cloud — https://arxiv.org/abs/2306.11346
- 3DGS-ReLoc — https://arxiv.org/abs/2403.11367
- Gaussian-LIC2 — https://arxiv.org/abs/2507.04004
- R-SCoRe — https://arxiv.org/abs/2501.01421
- Reloc3r — https://arxiv.org/abs/2412.08376
- Visual Localization in 3D Maps: Point Cloud, Mesh, and NeRF — https://arxiv.org/abs/2408.11966
- Visual-Inertial Localization With Prior LiDAR Map Constraints — https://april.zju.edu.cn/core/papercite-data/pdf/zuo2019visualinertiallw.pdf
- Monocular Camera Localization in Prior LiDAR Maps with 2D-3D Line Correspondences — https://arxiv.org/abs/2004.00740
- From LiDAR Maps to Visual Localization (แหล่งแนวคิด 2026) — https://arxiv.org/abs/2609.27363
- Environment-Adaptive Solid-State LiDAR-Inertial Odometry (แหล่งแนวคิด 2026) — https://arxiv.org/abs/2604.15864
- ISTD-LIOM (แหล่งแนวคิด 2026) — https://ijra.iaescore.com/index.php/IJRA/article/download/21115/13246
