// 인물 오려내기 마스크 — 맥 기본 Vision(VNGeneratePersonSegmentationRequest)으로 프레임마다 흑백 마스크 PNG를 만든다.
// 외부 전송 없음(기기 안에서 처리). 사용법: swift person_matte.swift <영상> <출력폴더>
// 그다음 ffmpeg alphamerge로 투명 인물 영상을 만든다(person_cutout.sh).
import AVFoundation
import CoreImage
import Vision
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count >= 3 else { print("사용법: person_matte.swift <영상> <출력폴더>"); exit(1) }
let url = URL(fileURLWithPath: args[1])
let outDir = URL(fileURLWithPath: args[2])
try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)

let asset = AVURLAsset(url: url)
let sem = DispatchSemaphore(value: 0)
var track: AVAssetTrack?
Task { track = try? await asset.loadTracks(withMediaType: .video).first; sem.signal() }
sem.wait()
guard let vt = track else { print("영상 트랙 없음"); exit(1) }
let reader = try AVAssetReader(asset: asset)
let output = AVAssetReaderTrackOutput(track: vt, outputSettings: [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
reader.add(output)
reader.startReading()

let req = VNGeneratePersonSegmentationRequest()
req.qualityLevel = .accurate
req.outputPixelFormat = kCVPixelFormatType_OneComponent8
let ctx = CIContext()
var i = 0
while let sb = output.copyNextSampleBuffer() {
    guard let pb = CMSampleBufferGetImageBuffer(sb) else { continue }
    let h = VNImageRequestHandler(cvPixelBuffer: pb, options: [:])
    try h.perform([req])
    guard let mask = req.results?.first?.pixelBuffer else { continue }
 // 마스크를 원본 크기로 키운다
    var m = CIImage(cvPixelBuffer: mask)
    let sx = CGFloat(CVPixelBufferGetWidth(pb)) / m.extent.width
    let sy = CGFloat(CVPixelBufferGetHeight(pb)) / m.extent.height
    m = m.transformed(by: CGAffineTransform(scaleX: sx, y: sy))
    let dst = outDir.appendingPathComponent(String(format: "m_%05d.png", i))
    if let cg = ctx.createCGImage(m, from: m.extent, format: .L8, colorSpace: CGColorSpaceCreateDeviceGray()),
       let d = CGImageDestinationCreateWithURL(dst as CFURL, UTType.png.identifier as CFString, 1, nil) {
        CGImageDestinationAddImage(d, cg, nil)
        CGImageDestinationFinalize(d)
    }
    i += 1
}
print("마스크 \(i)장 → \(outDir.path)")
