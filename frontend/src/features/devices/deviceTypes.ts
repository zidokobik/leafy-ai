import { DropletsIcon, FanIcon, FlaskConicalIcon, SunIcon, TestTubeIcon, type LucideIcon } from 'lucide-react'
import type { DeviceType } from '../../api/devices'

export const deviceTypes: { value: DeviceType, label: string, Icon: LucideIcon }[] = [
  { value: 'fan', label: 'Fan', Icon: FanIcon },
  { value: 'light', label: 'Light', Icon: SunIcon },
  { value: 'irrigation_pump', label: 'Irrigation pump', Icon: DropletsIcon },
  { value: 'ec_doser', label: 'EC doser', Icon: FlaskConicalIcon },
  { value: 'ph_doser', label: 'pH doser', Icon: TestTubeIcon },
]

export const deviceTypeMeta = Object.fromEntries(
  deviceTypes.map((type) => [type.value, type]),
) as Record<DeviceType, (typeof deviceTypes)[number]>
