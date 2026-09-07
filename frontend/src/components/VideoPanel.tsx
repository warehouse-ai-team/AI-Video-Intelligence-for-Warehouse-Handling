'use client';

import { useRef, useImperativeHandle, forwardRef } from 'react';

export interface VideoPanelHandle {
  seekTo: (seconds: number) => void;
}

interface VideoPanelProps {
  videoSrc?: string;
  activeLabel?: string; // e.g. video_id + created_at, for display only
  highlight?: React.ReactNode; // TimeRangeHighlight slots in below the player
}

const VideoPanel = forwardRef<VideoPanelHandle, VideoPanelProps>(
  ({ videoSrc, activeLabel, highlight }, ref) => {
    const videoElRef = useRef<HTMLVideoElement>(null);

    useImperativeHandle(ref, () => ({
      seekTo: (seconds: number) => {
        if (videoElRef.current) {
          videoElRef.current.currentTime = seconds;
          videoElRef.current.play().catch(() => {});
        }
      },
    }));

    return (
      <div className="flex h-full flex-col rounded-panel border border-border bg-surface">
        <div className="flex items-center justify-between border-b border-border px-4 py-2">
          <span className="text-sm font-medium text-text-primary">Video Feed</span>
          {activeLabel && <span className="data-readout text-xs text-text-muted">{activeLabel}</span>}
        </div>

        <div className="flex flex-1 items-center justify-center bg-base">
          {videoSrc ? (
            <video ref={videoElRef} src={videoSrc} controls className="h-full w-full object-contain" />
          ) : (
            <p className="text-sm text-text-muted">No video source connected yet</p>
          )}
        </div>

        {highlight && <div className="border-t border-border p-2">{highlight}</div>}
      </div>
    );
  }
);

VideoPanel.displayName = 'VideoPanel';
export default VideoPanel;