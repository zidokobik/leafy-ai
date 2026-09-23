
import { useState } from "react";
import { 
  Camera, Droplets, TestTube2, Sun, Wifi, WifiOff, 
  AlertTriangle, Video, X, Loader2, Gauge 
} from "lucide-react";

import { useFarmDevices, type Device, type DeviceType, type DeviceStatus } from "./useFarmDevice"; 
import basilFeedImg from "../../assets/basil-camera-feed.webp";

export function DevicesPage() {
  const { devices, cameraImages, isFetchingImages, toggleDevice } = useFarmDevices();
  
  const [filter, setFilter] = useState<DeviceType | "all">("all");
  const [activeCamera, setActiveCamera] = useState<Device | null>(null);

  const filteredDevices = filter === "all" ? devices : devices.filter(d => d.type === filter);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header & Filters */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Farm Devices</h1>
          <p className="text-gray-500 text-sm mt-1">Monitor and manage your hardware conditions.</p>
        </div>
        
        <div className="flex items-center gap-4">
          {isFetchingImages && <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />}
          <div className="flex bg-gray-100 dark:bg-gray-800 p-1 rounded-lg overflow-x-auto max-w-full">
            {["all", "camera", "pump", "doser", "light", "sensor"].map((type) => (
              <button
                key={type}
                onClick={() => setFilter(type as DeviceType | "all")}
                className={`px-4 py-2 text-sm font-medium rounded-md capitalize transition-colors whitespace-nowrap ${
                  filter === type 
                    ? "bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm" 
                    : "text-gray-600 dark:text-gray-400 hover:text-gray-900"
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Device Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {filteredDevices.map((device) => (
          <DeviceCard 
            key={device.id} 
            device={device} 
            onToggle={() => toggleDevice(device.id)} 
            onViewCamera={() => setActiveCamera(device)}
          />
        ))}
      </div>

      {/* Live Camera Feed Modal */}
      {activeCamera && (
        <CameraModal 
          camera={activeCamera} 
          imageUrl={cameraImages[activeCamera.id] || basilFeedImg} 
          onClose={() => setActiveCamera(null)} 
        />
      )}
    </div>
  );
}

// --- Subcomponent: Device Card ---
interface DeviceCardProps {
  device: Device;
  onToggle: () => void;
  onViewCamera: () => void;
}

function DeviceCard({ device, onToggle, onViewCamera }: DeviceCardProps) {
  const getTypeConfig = (type: DeviceType) => {
    switch(type) {
      case "camera": return { icon: Camera, color: "text-purple-500", bg: "bg-purple-100 dark:bg-purple-900/30" };
      case "pump": return { icon: Droplets, color: "text-blue-500", bg: "bg-blue-100 dark:bg-blue-900/30" };
      case "doser": return { icon: TestTube2, color: "text-amber-500", bg: "bg-amber-100 dark:bg-amber-900/30" };
      case "light": return { icon: Sun, color: "text-yellow-500", bg: "bg-yellow-100 dark:bg-yellow-900/30" };
      case "sensor": return { icon: Gauge, color: "text-emerald-500", bg: "bg-emerald-100 dark:bg-emerald-900/30" };
    }
  };

  const getStatusConfig = (status: DeviceStatus) => {
    switch(status) {
      case "online": return { icon: Wifi, color: "text-green-500", label: "Online" };
      case "offline": return { icon: WifiOff, color: "text-gray-400", label: "Offline" };
      case "warning": return { icon: AlertTriangle, color: "text-red-500", label: "Warning" };
    }
  };

  const TypeIcon = getTypeConfig(device.type).icon;
  const StatusIcon = getStatusConfig(device.status).icon;
  const isOff = device.status === "offline";
  const isSensor = device.type === "sensor";

  return (
    <div className={`p-5 rounded-xl border bg-white dark:bg-gray-900 transition-all ${
      isOff ? "border-gray-200 dark:border-gray-800 opacity-75" : "border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md"
    }`}>
      <div className="flex justify-between items-start mb-4">
        <div className={`p-2 rounded-lg ${getTypeConfig(device.type).bg}`}>
          <TypeIcon className={`w-6 h-6 ${getTypeConfig(device.type).color}`} />
        </div>
        <div className={`flex items-center gap-1.5 text-xs font-medium ${getStatusConfig(device.status).color}`}>
          <StatusIcon className="w-3.5 h-3.5" />
          {getStatusConfig(device.status).label}
        </div>
      </div>

      <div className="mb-6">
        <h3 className="font-semibold text-gray-900 dark:text-white truncate" title={device.name}>
          {device.name}
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {device.metrics}
        </p>
      </div>

      <div className="pt-4 border-t border-gray-100 dark:border-gray-800 flex justify-between items-center">
        {device.type === "camera" ? (
          <button 
            onClick={onViewCamera}
            disabled={isOff || !device.isActive}
            className={`flex items-center gap-1.5 text-sm font-medium transition-colors ${
              isOff || !device.isActive 
                ? "text-gray-400 cursor-not-allowed" 
                : "text-purple-600 hover:text-purple-700 dark:text-purple-400 dark:hover:text-purple-300"
            }`}
          >
            <Video className="w-4 h-4" />
            View Feed
          </button>
        ) : (
          <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            {isSensor ? "Monitoring" : (device.isActive ? "Running" : "Standby")}
          </span>
        )}
        
        <button
          onClick={onToggle}
          disabled={isOff || isSensor}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
            isOff || isSensor ? "bg-gray-200 dark:bg-gray-800 cursor-not-allowed" : 
            device.isActive ? "bg-green-500" : "bg-gray-300 dark:bg-gray-600"
          }`}
        >
          <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            device.isActive ? "translate-x-6" : "translate-x-1"
          }`} />
        </button>
      </div>
    </div>
  );
}

// --- Subcomponent: Camera Feed Modal ---
function CameraModal({ camera, imageUrl, onClose }: { camera: Device; imageUrl: string; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-4xl overflow-hidden border border-gray-200 dark:border-gray-800 animate-in fade-in zoom-in-95 duration-200">
        <div className="flex justify-between items-center p-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Camera className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h2 className="font-semibold text-gray-900 dark:text-white">{camera.name}</h2>
              <div className="flex items-center gap-2 text-xs">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                </span>
                <span className="text-red-500 font-medium">LIVE</span>
                <span className="text-gray-500 dark:text-gray-400 ml-2">{camera.metrics}</span>
              </div>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="relative aspect-video bg-black flex flex-col items-center justify-center group overflow-hidden">
          <img src={imageUrl} alt={`Live feed from ${camera.name}`} className="w-full h-full object-cover" />
          <div className="absolute bottom-0 inset-x-0 p-4 bg-gradient-to-t from-black/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="flex justify-between items-center text-white">
              <span className="text-sm font-medium shadow-sm">{camera.name} - Channel 1</span>
              <span className="text-sm font-mono bg-red-600/80 backdrop-blur-sm px-2 py-1 rounded">REC</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}