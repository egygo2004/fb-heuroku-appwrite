import { Client, Databases, Storage } from 'appwrite';

export const client = new Client();

client
    .setEndpoint('https://sfo.cloud.appwrite.io/v1')
    .setProject('6952e5ba002c94f9305c');

export const databases = new Databases(client);
export const storage = new Storage(client);

export const CONFIG = {
    DATABASE_ID: '6952e5fa00389b56379c',
    COLLECTION_NUMBERS: 'numbers',
    COLLECTION_LOGS: 'logs',
    BUCKET_ID: '6952e61e00371738e4bd'
};
