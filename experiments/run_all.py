"""Run all four experiments end-to-end."""
from common import banner

import exp1_intrinsic_accuracy
import exp2_bilinear_vs_linear
import exp3_delay_chain
import exp4_extrapolation


def main():
    exp1_intrinsic_accuracy.run()
    exp2_bilinear_vs_linear.run()
    exp3_delay_chain.run()
    exp4_extrapolation.run()

    banner("ALL EXPERIMENTS COMPLETED")
    print("  Results in: experiments/results/   (JSON + CSV)")
    print("  Figures in: experiments/figures/   (PNG)")


if __name__ == "__main__":
    main()
