/*
  Warnings:

  - Added the required column `rating` to the `Merchant` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
ALTER TABLE "Merchant" ADD COLUMN     "rating" INTEGER NOT NULL;
