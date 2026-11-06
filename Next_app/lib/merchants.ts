import { prisma } from "./prisma";

export async function createMerchant({
  userId,
  paypalMerchantId,
  name,
  email,
  domain,
}: {
  userId: string;
  paypalMerchantId: string;
  name: string;
  email: string;
  domain: string;
}) {
  return await prisma.merchant.create({
    data: {
      userId,
      paypalMerchantId,
      name,
      email,
      domain,
      // Other fields like dnsToken, emailCodeHash are left empty/null
      // and status defaults to PENDING_DNS
    },
  });
}

export async function getMerchantByEmail(email: string) {
  return await prisma.merchant.findUnique({
    where: { email },
  });
}

export async function fetchMerchantsToRefresh() {
    try{
        const sevenDaysAgo = new Date();
        sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
        const merchants = await prisma.merchant.findMany({
            where: {
                OR: [
            {
                lastRatingDate: {
                    lte: sevenDaysAgo
                }
            },
            {
                lastRatingDate: null
            }
        ]
            }
        });
        return merchants;
    }catch (error) {
        console.error("Error fetching merchants to refresh:", error);
        throw error;
    }
}

export async function fetchMerchantById(merchantId: string) {
    try{
        const merchants = await prisma.merchant.findUnique({
            where: {
                userId: merchantId,
            },
        });
        return merchants;
    }catch (error) {
        console.error("Error fetching merchants to refresh:", error);
        throw error;
    }
}
