
'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { Input } from './ui/input';
import { SearchIcon } from 'lucide-react';
import React from 'react';

export function Search() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const handleSearch = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const query = formData.get('search') as string;
    if (query) {
      router.push(`/search?q=${encodeURIComponent(query)}`);
    } else {
      router.push('/browse');
    }
  };

  return (
    <form onSubmit={handleSearch} className="relative w-full max-w-xs">
      <SearchIcon className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
      <Input
        name="search"
        placeholder="Search..."
        className="w-full pl-10"
        defaultValue={searchParams.get('q') || ''}
      />
    </form>
  );
}
