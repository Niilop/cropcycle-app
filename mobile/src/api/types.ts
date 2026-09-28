import type { components } from './schema'

type Schemas = components['schemas']

export type User = Schemas['UserResponse']
export type Token = Schemas['Token']
export type Garden = Schemas['GardenResponse']
export type GardenDetail = Schemas['GardenDetailResponse']
export type Bed = Schemas['BedResponse']
export type BedWrite = Schemas['BedWrite']
export type Crop = Schemas['CropResponse']
export type CropFamily = Schemas['CropFamilyResponse']
export type Planting = Schemas['PlantingResponse']
export type PlantingWrite = Schemas['PlantingWrite']
