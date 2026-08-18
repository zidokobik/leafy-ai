import { Icon } from '../../components/Icon'
import cameraFeed from '../../assets/basil-camera-feed.webp'

export function CameraPanel() {
  return (
    <article className="panel camera-panel">
      <div className="camera-panel-head">
        <div>
          <span className="section-kicker"><Icon name="camera" size={14} />Live camera</span>
          <h3>Sweet basil room</h3>
        </div>
        <button type="button" aria-label="Camera options"><Icon name="more" size={18} /></button>
      </div>

      <div className="camera-feed">
        <img src={cameraFeed} alt="Live view of Sweet basil growing in hydroponic rows" />
        <div className="camera-vignette" />
        <div className="camera-topline">
          <span className="live-badge"><i />LIVE</span>
          <span>CAM 01 · 1080p</span>
        </div>
        <div className="camera-caption">
          <div><strong>Main growing area</strong><small>Today · 10:42:18 AM</small></div>
          <span><Icon name="check" size={13} />Canopy clear</span>
        </div>
      </div>

      <div className="camera-footer">
        <span><i />Stream stable</span>
        <span>Plant coverage <strong>96%</strong></span>
        <button type="button">Open camera <Icon name="arrow" size={13} /></button>
      </div>
    </article>
  )
}
