import Foundation
import Vision
import AppKit
import ImageIO
import CoreGraphics

struct OCRBox: Codable {
    let t: String
    let c: Float
    let x0: Float
    let x1: Float
    let y0: Float
    let y1: Float
}

struct FrameOCR: Codable {
    let f: Int
    let items: [OCRBox]
}

let args = CommandLine.arguments
guard args.count >= 2 else {
    fputs("Usage: subtitle_ocr_mac <frames_dir> [lang_csv]\n", stderr)
    exit(1)
}

let framesDir = args[1]
let langCSV = args.count >= 3 ? args[2] : "zh-Hans,zh-Hant,en-US"
let recLangs = langCSV.split(separator: ",").map { String($0).trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }

let fm = FileManager.default
guard let entries = try? fm.contentsOfDirectory(atPath: framesDir) else {
    fputs("Cannot list directory: \(framesDir)\n", stderr)
    exit(1)
}

let jpgFiles: [(Int, String)] = entries.compactMap { name -> (Int, String)? in
    guard name.hasSuffix(".jpg") || name.hasSuffix(".jpeg") || name.hasSuffix(".png") else { return nil }
    let digits = name.unicodeScalars.filter { CharacterSet.decimalDigits.contains($0) }
    guard let idx = Int(String(String.UnicodeScalarView(digits))) else { return nil }
    return (idx, (framesDir as NSString).appendingPathComponent(name))
}.sorted { $0.0 < $1.0 }

if jpgFiles.isEmpty {
    exit(0)
}

// Tile `batchSize` horizontal subtitle strips vertically into one composite CGImage
// separated by `padPx` black bars so:
// 1. Subtitles near the bottom edge always have clean black margin (preventing edge-clipping misses)
// 2. XPC / ANE invocation overhead drops by 10x (6-minute video finishes in ~7s; 2-hour movie in ~80s!)
let batchSize = 10
let padPx = 18
let totalFrames = jpgFiles.count
let numBatches = (totalFrames + batchSize - 1) / batchSize
var allResults = Array<FrameOCR?>(repeating: nil, count: totalFrames)
let lock = NSLock()
let colorSpace = CGColorSpaceCreateDeviceRGB()

DispatchQueue.concurrentPerform(iterations: numBatches) { bIdx in
    autoreleasepool {
        let startI = bIdx * batchSize
        let endI = min(totalFrames, startI + batchSize)
        let count = endI - startI
        if count <= 0 { return }

        var loaded: [(Int, Int, CGImage)] = []
        loaded.reserveCapacity(count)
        var maxW = 0
        var stripH = 0

        for i in startI..<endI {
            let (frameIdx, path) = jpgFiles[i]
            let url = URL(fileURLWithPath: path)
            if let src = CGImageSourceCreateWithURL(url as CFURL, nil),
               let img = CGImageSourceCreateImageAtIndex(src, 0, nil) {
                loaded.append((i, frameIdx, img))
                if img.width > maxW { maxW = img.width }
                if stripH == 0 { stripH = img.height }
            }
        }
        if loaded.isEmpty || maxW == 0 || stripH == 0 { return }

        let slotH = stripH + padPx
        let canvasH = loaded.count * slotH + padPx

        guard let ctx = CGContext(
            data: nil,
            width: maxW,
            height: canvasH,
            bitsPerComponent: 8,
            bytesPerRow: maxW * 4,
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue
        ) else {
            return
        }

        // Fill black background so every strip has clean black top/bottom padding
        ctx.setFillColor(red: 0, green: 0, blue: 0, alpha: 1)
        ctx.fill(CGRect(x: 0, y: 0, width: maxW, height: canvasH))

        // CoreGraphics origin (0,0) is bottom-left (matching Vision normalized boundingBox!)
        // Place slot k at y = padPx + k * slotH
        for (k, item) in loaded.enumerated() {
            let yBottom = padPx + k * slotH
            ctx.draw(item.2, in: CGRect(x: 0, y: yBottom, width: item.2.width, height: stripH))
        }

        guard let composite = ctx.makeImage() else { return }

        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.usesLanguageCorrection = true
        if !recLangs.isEmpty {
            request.recognitionLanguages = recLangs
        }

        let handler = VNImageRequestHandler(cgImage: composite, options: [:])
        do {
            try handler.perform([request])
        } catch {
            return
        }

        guard let observations = request.results, !observations.isEmpty else { return }

        var perSlot = Array<[OCRBox]>(repeating: [], count: loaded.count)
        let canvasHf = Float(canvasH)
        let stripHf = Float(stripH)
        let slotHf = Float(slotH)
        let padPxf = Float(padPx)

        for obs in observations {
            guard let top = obs.topCandidates(1).first else { continue }
            let txt = top.string.trimmingCharacters(in: .whitespacesAndNewlines)
            if txt.isEmpty || top.confidence < 0.30 { continue }
            let bb = obs.boundingBox
            let midY_px = Float(bb.midY) * canvasHf
            let k = Int(floor((midY_px - padPxf * 0.5) / slotHf))
            if k < 0 || k >= loaded.count { continue }

            let slotBottomPx = padPxf + Float(k) * slotHf
            let relY0 = max(0.0, min(1.0, (Float(bb.minY) * canvasHf - slotBottomPx) / stripHf))
            let relY1 = max(0.0, min(1.0, (Float(bb.maxY) * canvasHf - slotBottomPx) / stripHf))

            perSlot[k].append(OCRBox(
                t: txt,
                c: Float(top.confidence),
                x0: Float(bb.minX),
                x1: Float(bb.maxX),
                y0: relY0,
                y1: relY1
            ))
        }

        lock.lock()
        for (k, boxes) in perSlot.enumerated() {
            if !boxes.isEmpty {
                let (arrIdx, frameIdx, _) = loaded[k]
                allResults[arrIdx] = FrameOCR(f: frameIdx, items: boxes)
            }
        }
        lock.unlock()
    }
}

let encoder = JSONEncoder()
let outHandle = FileHandle.standardOutput
let nl = Data([0x0A])

for r in allResults {
    if let item = r, let data = try? encoder.encode(item) {
        outHandle.write(data)
        outHandle.write(nl)
    }
}
