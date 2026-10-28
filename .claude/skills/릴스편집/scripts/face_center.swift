// 얼굴 가운데 찾기 — 맥 Vision 얼굴 인식(기기 안 처리, 외부 전송 없음).
// 사용법: face_center <사진> [사진 ...] → 줄마다 "사진경로\tfx\tfy" (0~1, 왼쪽 위 기준). 얼굴이 없으면 -1 -1.
// 가장 큰 얼굴 하나만 쓴다.
import Foundation
import Vision
import AppKit

for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        print("\(path)\t-1\t-1"); continue
    }
    let req = VNDetectFaceRectanglesRequest()
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    let faces = (req.results ?? []).sorted { $0.boundingBox.width * $0.boundingBox.height > $1.boundingBox.width * $1.boundingBox.height }
    if let f = faces.first {
        let b = f.boundingBox
        print(String(format: "%@\t%.4f\t%.4f", path, b.midX, 1 - b.midY))
    } else {
        print("\(path)\t-1\t-1")
    }
}
