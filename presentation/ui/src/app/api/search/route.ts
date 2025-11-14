
import { NextRequest, NextResponse } from 'next/server';
import { searchVAIS } from '@/lib/vais';

export async function POST(req: NextRequest) {
  try {
    const { query } = await req.json();

    if (!query) {
      return NextResponse.json({ error: 'Query is required' }, { status: 400 });
    }

    const results = await searchVAIS(query);
    return NextResponse.json(results);

  } catch (error: any) {
    console.error('Error in search API route:', error);
    return NextResponse.json({ error: error.message || 'An unexpected error occurred.' }, { status: 500 });
  }
}
