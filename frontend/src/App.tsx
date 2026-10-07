import React from 'react';
import { TopBanner } from './components/TopBanner';
import { Navbar } from './components/Navbar';
import { HeroSection } from './components/HeroSection';
import { ActionSimulator } from './components/ActionSimulator';
import { FeaturesGrid } from './components/FeaturesGrid';
import { BenchmarkTable } from './components/BenchmarkTable';
import { Footer } from './components/Footer';

export const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#fcfbfa] flex flex-col font-sans text-[#111111]">
      <TopBanner />
      <Navbar />
      <main className="flex-1">
        <HeroSection />
        <ActionSimulator />
        <FeaturesGrid />
        <BenchmarkTable />
      </main>
      <Footer />
    </div>
  );
};

export default App;
