// lib/db.ts

import { PrismaClient } from '@prisma/client'

declare global {
  // allow global `var` declarations
  // eslint-disable-next-line no-var
  var prisma: PrismaClient | undefined
}


// This prevents instantiating multiple PrismaClient instances in development
export const db =
  global.prisma ||
  new PrismaClient({
    // Optional: log all queries to the console
    // log: ['query'],
  })

if (process.env.NODE_ENV !== 'production') {
  global.prisma = db
}