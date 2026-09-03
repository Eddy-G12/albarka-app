/**
 * src/components/charts/ChartWrapper.tsx
 * =======================================
 * Enveloppe n'importe quel graphique Recharts avec :
 *   - Boutons zoom +  / zoom −  / reset (transform: scale CSS)
 *   - Bouton téléchargement PNG via extraction SVG → canvas (natif, sans lib)
 */

import React, { useRef, useState, useCallback } from 'react';
import { DownloadIcon, ZoomInIcon, ZoomOutIcon } from 'lucide-react';

interface ChartWrapperProps {
  children: React.ReactNode;
  titre?: string;
  className?: string;
}

const ZOOM_STEP = 0.15;
const ZOOM_MIN  = 0.5;
const ZOOM_MAX  = 3;

/**
 * Rasterise le SVG Recharts en PNG.
 *
 * Recharts pose les couleurs directement comme attributs SVG (fill="…").
 * On ne touche PAS aux styles calculés pour éviter de capturer le fond sombre
 * de la page. On ajoute uniquement un rect blanc en fond et on sérialise.
 */
async function svgToPng(container: HTMLElement): Promise<string> {
  const svg = container.querySelector('svg');
  if (!svg) throw new Error('Aucun SVG trouvé dans le graphique.');

  const rect = svg.getBoundingClientRect();
  const w = Math.round(rect.width)  || 800;
  const h = Math.round(rect.height) || 400;

  const clone = svg.cloneNode(true) as SVGElement;
  clone.setAttribute('width',  String(w));
  clone.setAttribute('height', String(h));
  clone.setAttribute('xmlns',  'http://www.w3.org/2000/svg');

  // Fond blanc explicite — évite le fond noir par défaut du canvas
  const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  bg.setAttribute('width',  '100%');
  bg.setAttribute('height', '100%');
  bg.setAttribute('fill',   '#ffffff');
  clone.insertBefore(bg, clone.firstChild);

  // Pour les éléments qui ont fill/stroke définis UNIQUEMENT via CSS (classe Tailwind, etc.),
  // on copie la valeur calculée en attribut direct — mais seulement si elle n'est pas
  // héritée du fond sombre (noir ou transparent).
  const srcEls = Array.from(svg.querySelectorAll('[class]'));
  const dstEls = Array.from(clone.querySelectorAll('[class]'));
  srcEls.forEach((src, i) => {
    const dst = dstEls[i];
    if (!dst) return;
    const cs = window.getComputedStyle(src);

    const cFill = cs.fill;
    if (
      !src.getAttribute('fill') &&
      cFill &&
      cFill !== 'none' &&
      cFill !== 'rgb(0, 0, 0)' &&       // noir = héritage du fond, on l'ignore
      cFill !== 'rgba(0, 0, 0, 0)'      // transparent idem
    ) {
      dst.setAttribute('fill', cFill);
    }

    const cStroke = cs.stroke;
    if (!src.getAttribute('stroke') && cStroke && cStroke !== 'none') {
      dst.setAttribute('stroke', cStroke);
    }
  });

  const svgString = new XMLSerializer().serializeToString(clone);
  const blob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' });
  const url  = URL.createObjectURL(blob);

  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const scale  = 2; // résolution ×2 pour écrans Retina
      const canvas = document.createElement('canvas');
      canvas.width  = w * scale;
      canvas.height = h * scale;
      const ctx = canvas.getContext('2d')!;
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.scale(scale, scale);
      ctx.drawImage(img, 0, 0, w, h);
      URL.revokeObjectURL(url);
      resolve(canvas.toDataURL('image/png'));
    };
    img.onerror = (e) => { URL.revokeObjectURL(url); reject(e); };
    img.src = url;
  });
}

export function ChartWrapper({ children, titre = 'graphique', className = '' }: ChartWrapperProps) {
  const [zoom, setZoom] = useState(1);
  const [downloading, setDownloading] = useState(false);
  const innerRef = useRef<HTMLDivElement>(null);

  const zoomIn  = () => setZoom((z) => Math.min(+(z + ZOOM_STEP).toFixed(2), ZOOM_MAX));
  const zoomOut = () => setZoom((z) => Math.max(+(z - ZOOM_STEP).toFixed(2), ZOOM_MIN));
  const reset   = () => setZoom(1);

  const download = useCallback(async () => {
    if (!innerRef.current || downloading) return;
    setDownloading(true);
    try {
      const dataUrl = await svgToPng(innerRef.current);
      const a = document.createElement('a');
      a.href     = dataUrl;
      a.download = `${titre.replace(/[^a-z0-9-_]/gi, '_').toLowerCase()}.png`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (err) {
      console.error('Erreur export PNG :', err);
      alert("Impossible de générer l'image. Vérifiez la console pour plus de détails.");
    } finally {
      setDownloading(false);
    }
  }, [downloading, titre]);

  const pct = Math.round(zoom * 100);

  return (
    <div className={`relative ${className}`}>
      {/* Barre d'outils */}
      <div className="absolute top-1 right-1 z-10 flex items-center gap-1 bg-white/80 backdrop-blur-sm border border-gray-200 rounded-lg px-1.5 py-1 shadow-sm">
        <button
          onClick={zoomOut}
          disabled={zoom <= ZOOM_MIN}
          title="Zoom arrière"
          className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          aria-label="Zoom arrière"
        >
          <ZoomOutIcon className="h-3.5 w-3.5 text-gray-600" />
        </button>

        <button
          onClick={reset}
          title="Réinitialiser le zoom"
          className="px-1.5 py-0.5 text-[10px] font-mono text-gray-500 hover:bg-gray-100 rounded transition-colors min-w-[36px] text-center"
          aria-label="Réinitialiser le zoom"
        >
          {pct}%
        </button>

        <button
          onClick={zoomIn}
          disabled={zoom >= ZOOM_MAX}
          title="Zoom avant"
          className="p-1 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          aria-label="Zoom avant"
        >
          <ZoomInIcon className="h-3.5 w-3.5 text-gray-600" />
        </button>

        <div className="w-px h-4 bg-gray-200 mx-0.5" />

        <button
          onClick={download}
          disabled={downloading}
          title="Télécharger en PNG"
          className="p-1 rounded hover:bg-gray-100 disabled:opacity-50 disabled:cursor-wait transition-colors"
          aria-label="Télécharger en PNG"
        >
          <DownloadIcon
            className={`h-3.5 w-3.5 ${downloading ? 'text-gray-300 animate-pulse' : 'text-gray-600'}`}
          />
        </button>
      </div>

      {/* Zone scrollable si zoom > 1 */}
      <div
        className="overflow-auto"
        style={{ maxHeight: zoom > 1 ? '600px' : undefined }}
      >
        <div
          ref={innerRef}
          style={{
            transform: `scale(${zoom})`,
            transformOrigin: 'top left',
            width: zoom !== 1 ? `${(100 / zoom).toFixed(1)}%` : '100%',
            transition: 'transform 0.15s ease',
          }}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
