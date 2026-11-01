// QR codes for authenticator setup (qrcode-generator, MIT, Kazuhiko Arase).
import qrcode from 'qrcode-generator';

// Returns an SVG string; drawn with rects only, so the CSP needs no inline script.
export function qrSvg(text) {
  const qr = qrcode(0, 'M');
  qr.addData(text);
  qr.make();
  return qr.createSvgTag({cellSize: 4, margin: 4, scalable: true});
}
