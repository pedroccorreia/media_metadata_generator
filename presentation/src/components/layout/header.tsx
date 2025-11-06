
"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useSearchParams } from "next/navigation";
import { Clapperboard, Menu, Search as SearchIcon, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { Suspense, useState, useEffect } from "react";
import { Search } from "@/components/search";
import { Input } from "../ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";


const navItems = [
  { href: "/browse", label: "Home" },
  { href: "/movies", label: "Movies" },
  { href: "/tv-shows", label: "TV Shows" },
  { href: "/inspire-me", label: "What to Watch" },
];

const SearchFallback = () => {
    return (
        <div className="relative w-full max-w-xs">
             <SearchIcon className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" />
            <Input
                placeholder="Search..."
                className="w-full pl-10"
                disabled
            />
        </div>
    )
}

const ProfileAvatar = () => {
  const searchParams = useSearchParams();
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);

  useEffect(() => {
    setAvatarUrl(searchParams.get('avatar'));
  }, [searchParams]);

  if (!avatarUrl) {
    return null;
  }

  return (
    <Link href="/profiles">
      <Avatar className="h-8 w-8 cursor-pointer">
        <AvatarImage src={avatarUrl} alt="User profile" />
        <AvatarFallback>
          <User />
        </AvatarFallback>
      </Avatar>
    </Link>
  );
};


export function Header() {
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const NavLink = ({ href, label }: { href: string; label: string }) => (
    <Link
      href={href}
      className={cn(
        "text-sm font-medium transition-colors hover:text-primary",
        pathname === href ? "text-primary" : "text-muted-foreground"
      )}
      onClick={() => setIsMobileMenuOpen(false)}
    >
      {label}
    </Link>
  );

  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        <div className="mr-4 hidden items-center md:flex">
          <Link href="/profiles" className="mr-6 flex items-center space-x-2">
            <Clapperboard className="h-6 w-6 text-primary" />
            <span className="hidden font-bold sm:inline-block">CineShorts</span>
          </Link>
          <nav className="flex items-center space-x-6 text-sm font-medium">
            {navItems.map((item) => (
              <NavLink key={item.href} {...item} />
            ))}
          </nav>
        </div>

        {/* Mobile Menu */}
        <div className="md:hidden">
          <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon">
                <Menu className="h-5 w-5" />
                <span className="sr-only">Open Menu</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="left">
              <div className="flex flex-col gap-6">
                <Link href="/profiles" className="flex items-center space-x-2" onClick={() => setIsMobileMenuOpen(false)}>
                  <Clapperboard className="h-6 w-6 text-primary" />
                  <span className="font-bold">CineShorts</span>
                </Link>
                <nav className="flex flex-col gap-4">
                  {navItems.map((item) => (
                    <NavLink key={item.href} {...item} />
                  ))}
                </nav>
              </div>
            </SheetContent>
          </Sheet>
        </div>

        <div className="flex flex-1 items-center justify-end gap-4">
          <Suspense fallback={<SearchFallback />}>
            <Search />
          </Suspense>
          <Suspense fallback={null}>
             <ProfileAvatar />
          </Suspense>
        </div>
      </div>
    </header>
  );
}
