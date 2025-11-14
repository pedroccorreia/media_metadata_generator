
import Link from 'next/link';
import Image from 'next/image';
import { Card, CardContent } from '@/components/ui/card';

const profiles = [
  { name: 'Thomas', avatarUrl: 'https://images.unsplash.com/photo-1640951613773-54706e06851d?w=1080&q=80', hint: 'man avatar' },
  { name: 'Matilda', avatarUrl: 'https://images.unsplash.com/photo-1580489944761-15a19d654956?w=1080&q=80', hint: 'woman avatar' },
  { name: 'Kids', avatarUrl: 'https://images.unsplash.com/photo-1630476504743-a4d342f88760?w=1080&q=80', hint: 'kids drawing' },
];

export default function ProfilesPage() {
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center text-foreground p-4">
      <div className="text-center mb-12">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight">Who's watching?</h1>
      </div>
      <div className="flex flex-col sm:flex-row items-center justify-center gap-4 md:gap-8">
        {profiles.map((profile) => (
          <Link 
            href={`/browse?profile=${encodeURIComponent(profile.name)}&avatar=${encodeURIComponent(profile.avatarUrl)}`} 
            key={profile.name} 
            className="group"
          >
            <div className="flex flex-col items-center gap-3">
              <Card className="w-32 h-32 md:w-40 md:h-40 rounded-full overflow-hidden border-4 border-transparent group-hover:border-primary transition-all duration-300">
                <CardContent className="p-0 relative w-full h-full">
                  <Image
                    src={profile.avatarUrl}
                    alt={profile.name}
                    data-ai-hint={profile.hint}
                    fill
                    sizes="(max-width: 768px) 128px, 160px"
                    className="object-cover transition-transform duration-300 group-hover:scale-110"
                  />
                </CardContent>
              </Card>
              <h2 className="text-xl font-semibold text-muted-foreground group-hover:text-foreground transition-colors">
                {profile.name}
              </h2>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
