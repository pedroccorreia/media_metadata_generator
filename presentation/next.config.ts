
import type {NextConfig} from 'next';

const nextConfig: NextConfig = {
  /* config options here */
  typescript: {
    ignoreBuildErrors: true,
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**',
      },
       {
        protocol: 'http',
        hostname: '**',
      },
    ],
  },
  allowedDevOrigins: ['9000-firebase-me-showcase-1755148887606.cluster-ys234awlzbhwoxmkkse6qo3fz6.cloudworkstations.dev', 'http://localhost'],
};

export default nextConfig;
