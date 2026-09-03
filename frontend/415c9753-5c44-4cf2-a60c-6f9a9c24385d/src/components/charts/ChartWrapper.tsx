/**
 * src/components/charts/ChartWrapper.tsx
 * =======================================
 * Enveloppe n'importe quel graphique Recharts avec :
 *   - Boutons zoom +  / zoom −  / reset (transform: scale CSS)
 *   - Bouton téléchargement PNG via html-to-image
 *
 * Usage :
 *   <ChartWrapper titre="Cash In">
 *     <BarresHorizontales ... />
 *   </ChartWrapper>
 */

import React, { useRef, useState, useCallback } from 'react';
import { toPng } from 'html-to-image';
import { DownloadIcon, ZoomInIcon, ZoomOutIcon, Maximize2Icon } from 'lucide-react';

interface ChartWrapperProps {
  children: React.ReactNode;
  /** Nom du fichier PNG téléchargé (sans extension) */
  titre?: string;
  /** Classe CSS additionnelle sur le conteneur extérieur */
  className?: string;
}

const ZOOM_STEP = 0.15;
const ZOOM_MIN  = 0.5;
const ZOOM_MAX  = 3;

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
    // On capture à zoom = 1 pour avoir une image nette quelle que soit la vue courante
    const prevZoom = zoom;
    setZoom(1);
    // Attendre le repaint
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r as () => void)));
    try {
      const dataUrl = await toPng(innerRef.current, {
        backgroundColor: '#ffffff',
        pixelRatio: 2,          // résolution ×2 pour écrans Retina
        style: { borderRadius: '0' },
      });
      const a = document.createElement('a');
      a.href = dataUrl;
      a.download = `${titre.replace(/[^a-z0-9-_]/gi, '_').toLowerCase()}.png`;
      a.click();
    } catch (err) {
      console.error('Erreur export PNG :', err);
    } finally {
      setZoom(prevZoom);
      setDownloading(false);
    }
  }, [downloading, titre, zoom]);

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
          {downloading
            ? <Maximize2Icon className="h-3.5 w-3.5 text-gray-400 animate-pulse" />
            : <DownloadIcon className="h-3.5 w-3.5 text-gray-600" />}
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
