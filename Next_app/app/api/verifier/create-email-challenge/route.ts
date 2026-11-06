import { NextResponse } from "next/server";
import {createEmailChallengeCode} from '@/lib/emailVerifier'

export async function POST(req:Request){
    try{
        const body=await req.json();
        const {email}=body;
        createEmailChallengeCode(email);
        return NextResponse.json({message:"Verification Code sent"});
    }
    catch(err){
        console.log(err);
        return NextResponse.json({message:"Error in Creating Email challlenge please try again"})
    }
}