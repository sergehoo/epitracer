'use client';

import { useRegistrationStore } from '@/lib/store';
import { Section } from '@/components/ui/Section';
import { StepIndicator } from '@/components/form/StepIndicator';
import { Step1Voyage } from '@/components/form/steps/Step1Voyage';
import { Step2Identite } from '@/components/form/steps/Step2Identite';
import { Step3Historique } from '@/components/form/steps/Step3Historique';
import { Step4Confinement } from '@/components/form/steps/Step4Confinement';
import { Step5Exposure } from '@/components/form/steps/Step5Exposure';
import { Step6Symptoms } from '@/components/form/steps/Step6Symptoms';
import { Step7Declaration } from '@/components/form/steps/Step7Declaration';

export default function VoyageurPage() {
  const { step, goTo } = useRegistrationStore();

  const next = () => goTo(Math.min(step + 1, 6));
  const back = () => goTo(Math.max(step - 1, 0));

  return (
    <Section
      eyebrow="Fiche de renseignement passager — Maladie à Virus Ebola (MVE)"
      title="Fiche passager — accompagnement sanitaire"
      description="Vos informations permettent à l'INHP de vous accompagner durant votre séjour. Vos données sont chiffrées et utilisées exclusivement à des fins de suivi sanitaire."
    >
      <div className="card p-6 lg:p-10">
        <StepIndicator current={step} onJump={(i) => goTo(i)} />
        <div className="animate-fade-up">
          {step === 0 && <Step1Voyage onNext={next} />}
          {step === 1 && <Step2Identite onNext={next} onBack={back} />}
          {step === 2 && <Step3Historique onNext={next} onBack={back} />}
          {step === 3 && <Step4Confinement onNext={next} onBack={back} />}
          {step === 4 && <Step5Exposure onNext={next} onBack={back} />}
          {step === 5 && <Step6Symptoms onNext={next} onBack={back} />}
          {step === 6 && <Step7Declaration onBack={back} />}
        </div>
      </div>
    </Section>
  );
}
