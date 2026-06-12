import AppKit
import CoreText
import Foundation

func fail(_ message: String) -> Never {
    FileHandle.standardError.write((message + "\n").data(using: .utf8)!)
    exit(1)
}

func color(from hex: String) -> NSColor {
    let trimmed = hex.trimmingCharacters(in: CharacterSet(charactersIn: "#"))
    guard trimmed.count == 6, let value = Int(trimmed, radix: 16) else {
        return NSColor(calibratedRed: 0.35, green: 0.78, blue: 0.98, alpha: 1)
    }

    return NSColor(
        calibratedRed: CGFloat((value >> 16) & 0xff) / 255,
        green: CGFloat((value >> 8) & 0xff) / 255,
        blue: CGFloat(value & 0xff) / 255,
        alpha: 1
    )
}

func makeFont(from path: String, size: CGFloat) -> CTFont {
    let url = URL(fileURLWithPath: path)
    guard let dataProvider = CGDataProvider(url: url as CFURL) else {
        fail("Could not read font: \(path)")
    }

    guard let cgFont = CGFont(dataProvider) else {
        fail("Could not load font: \(path)")
    }

    return CTFontCreateWithGraphicsFont(cgFont, size, nil, nil)
}

func render(glyph: String, outputPath: String, font: CTFont, canvasSize: Int, fillColor: NSColor) throws {
    let size = CGFloat(canvasSize)
    let colorSpace = CGColorSpaceCreateDeviceRGB()
    guard let context = CGContext(
        data: nil,
        width: canvasSize,
        height: canvasSize,
        bitsPerComponent: 8,
        bytesPerRow: 0,
        space: colorSpace,
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    ) else {
        fail("Could not create graphics context")
    }

    context.clear(CGRect(x: 0, y: 0, width: size, height: size))
    context.setAllowsAntialiasing(true)
    context.setShouldAntialias(true)

    let attributes: [NSAttributedString.Key: Any] = [
        NSAttributedString.Key(kCTFontAttributeName as String): font,
        NSAttributedString.Key(kCTForegroundColorAttributeName as String): fillColor.cgColor,
    ]

    let attributedString = NSAttributedString(string: glyph, attributes: attributes)
    let line = CTLineCreateWithAttributedString(attributedString)
    let bounds = CTLineGetBoundsWithOptions(line, [.useGlyphPathBounds])
    let x = (size - bounds.width) / 2 - bounds.minX
    let y = (size - bounds.height) / 2 - bounds.minY

    context.textPosition = CGPoint(x: x, y: y)
    CTLineDraw(line, context)

    guard let image = context.makeImage() else {
        fail("Could not create image")
    }

    let bitmap = NSBitmapImageRep(cgImage: image)
    guard let pngData = bitmap.representation(using: .png, properties: [:]) else {
        fail("Could not encode PNG")
    }

    let outputURL = URL(fileURLWithPath: outputPath)
    try FileManager.default.createDirectory(at: outputURL.deletingLastPathComponent(), withIntermediateDirectories: true)
    try pngData.write(to: outputURL)
}

let args = Array(CommandLine.arguments.dropFirst())
guard args.count >= 5, (args.count - 3) % 2 == 0 else {
    fail("Usage: render-icon FONT_PATH SIZE HEX_COLOR GLYPH OUTPUT_PATH [GLYPH OUTPUT_PATH ...]")
}

let fontPath = args[0]
let canvasSize = Int(args[1]) ?? 96
let fillColor = color(from: args[2])
let font = makeFont(from: fontPath, size: CGFloat(canvasSize) * 0.72)
let pairs = Array(args.dropFirst(3))

for index in stride(from: 0, to: pairs.count, by: 2) {
    try render(glyph: pairs[index], outputPath: pairs[index + 1], font: font, canvasSize: canvasSize, fillColor: fillColor)
}
