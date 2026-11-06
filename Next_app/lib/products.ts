import {prisma} from './prisma'

const AI_URL=process.env.AI_BASE_URL

export async function getProductById(productId: string){

    const product=await prisma.product.findUnique(
            {
                where:{
                    id:productId,
                },
            }
        )

        if(!product)  throw new Error("Product Not Found");
        try{
        const result=await fetch(`${AI_URL}/ai/embed-product`,{
                method:"POST",
                headers:{
                    "Content-Type": "application/json",
                },
                    body: JSON.stringify({
                    productId: product?.id,
                    name: product?.name,
                    description: product?.description,
                    category: product?.keywords,
                }),
                }
            )
            const embedd=await result.json();
            return embedd;
        }catch(err){
        throw new Error("error in fetching embedd from ai backend");
    }

}

export async function updateProductById(
    productId:string,embed:number[]
){
    try{
        const vectorString = `[${embed.join(",")}]`;

        await prisma.$executeRaw`
            UPDATE "Product"
            SET "embeddedString" = ${vectorString}::vector
            WHERE "id" = ${productId}
        `;

        return { success: true };
    }catch(err){
        console.log(err);
        throw new Error("error in updating product"); 
    }
}