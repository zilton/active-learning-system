package weka.classifiers.rules;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.util.ArrayList;
import java.util.Iterator;

public class Main {
	public float f1(){
		return 0.0f;
	}
	
	
	
	public static ArrayList<String> process(String filename, double percentual, int m, double[] threshold) throws Exception {

		boolean debug = false;
		int maxRuleSize = m;
		double minSupport = 0.00001;
		double minConfidence = 0.0001;

		boolean considerFeaturePosition = false;

		BufferedReader reader = new BufferedReader(new FileReader(filename));
		
		String line;
		
		
		ArrayList<String> linhasTreino = new ArrayList<String>();
		ArrayList<String> linhasTeste = new ArrayList<String>();
		ArrayList<String> lines = new ArrayList<String>();
		ArrayList<String> linhasArquivo = new ArrayList<String>();
		ArrayList<String> resultados = new ArrayList<String>();
		double[] acuracias = new double[10];
		
		while ((line = reader.readLine()) != null) {
			lines.add(line);
		}

		
		int max_fold = 10;
		int fold = 0;
		int intervalo= 458;

		for (Iterator<String> iterator = lines.iterator(); iterator.hasNext();) {
			line = (String) iterator.next();
			linhasArquivo.add(line);
		}
		reader.close();
		
		for(fold=0; fold<max_fold;fold++){
			LACInstances training = new LACInstances(considerFeaturePosition);
			ArrayList<LACInstance> treino = new ArrayList<LACInstance>();
			ArrayList<LACInstance> teste = new ArrayList<LACInstance>();
			teste.clear();
			treino.clear();
			int start = fold * intervalo;
			int end = (fold+1) * intervalo;
			double hits = 0;
			//separa linhas de treino e teste
			separa_treino_teste(linhasTreino, linhasTeste, linhasArquivo,
					start, end);
			
			/* Prepara o treino */
			prepara_instancias_treino(training, treino, linhasTreino);
			
			LACRules lac = training.prepare(maxRuleSize - 1, minSupport, minConfidence, considerFeaturePosition, debug);
			
			/* Prepara o teste */
			//int[][] confusao = {new int[]double hits = 0;{0, 0, 0, 0, 0}, new int[]{0, 0, 0, 0, 0}, new int[]{0, 0, 0, 0, 0}, new int[]{0, 0, 0, 0, 0}, new int[]{0, 0, 0, 0, 0}, new int[]{0, 0, 0, 0, 0}};
			for (String l: linhasTeste) {
				
				String[] partes = l.split(" ");
				if (partes.length > 2){
					LACInstance instance = training.createNewTrainingInstance();
					teste.add(instance);
					instance.setId(partes[0]);
					instance.setClass(partes[1].substring(6));
					for (int i = 2; i < partes.length; i++) {
						boolean gram = partes[i].indexOf('_') == -1 || true;
						if (partes[i].length() > 3 && gram)
							instance.addFeature(partes[i].substring(2));
					}
					
					double[] probabilities = lac.calculateProbabilities(instance);
					
					int maxIndex = 0;
					for (int i = 0; i < probabilities.length; i++) {
						if (threshold.length > 0){
							if (probabilities[i] >= threshold[i]){
								maxIndex = i;
								break;
							}
						} else if (probabilities[maxIndex] < probabilities[i]){
							maxIndex = i;
//							maxValue = probabilities[i];
						}
					}
					LACClass klass = training.getClassByIndex(maxIndex);
					LACClass original = instance.getClazz();
					
					if(klass.getLabel().equals(original.getLabel())) hits++;
					//confusao[Integer.parseInt(original.getLabel())][Integer.parseInt(klass.getLabel())] ++;
					//resultados.add(instance.getId() + " " + original.getLabel() + " " + klass.getLabel() + " " + instance.getNumRules() + " " + probabilities[maxIndex] );
					//resultados.addAll(instance.getRules());
					//instance.printRules();
				} // fim if
			}
			acuracias[fold] = hits/linhasTeste.size();
			//System.out.println("Acuracia para fold " + fold + " :" + acuracias[fold]);
		}
		
		double media = getMean(acuracias);
		double deviation = getDeviantion(acuracias, media);
		System.out.println(media + "+/-" + deviation);
	    //System.out.prinln("Media %.3f%n +/- %.3f%n", stat.getMedian(acuracias), stat.getStandardDev(acuracias, stat.getMedian(acuracias)));
		return resultados;
	}

	private static double getMean(double[] valores){
		double total = 0;
		for(int i=0; i< valores.length;i++) total += valores[i];
		return total/valores.length;
			
	}
	private static double getDeviantion(double[] valores, double media){
		double soma = 0;
		for(int i=0; i < valores.length; i++)
			soma += Math.pow(valores[i]-media,2);
		return Math.sqrt(soma/valores.length);
		
	}
	private static void prepara_instancias_treino(LACInstances training,
			ArrayList<LACInstance> treino, ArrayList<String> linhasTreino) {
		treino.clear();
		for (String l: linhasTreino) {
			String[] partes = l.split(" ");
			if (partes.length > 2){
				LACInstance instance = training.createNewTrainingInstance();
				treino.add(instance);
				instance.setId(partes[0]);
				instance.setClass(partes[1].substring(6));
				for (int i = 2; i < partes.length; i++) {
					boolean gram = partes[i].indexOf('_') == -1 || true;
					if (partes[i].length() > 3 && gram)
						instance.addFeature(partes[i].substring(2));
				}
			}
		}
	}

	private static void separa_treino_teste(ArrayList<String> linhasTreino,
			ArrayList<String> linhasTeste, ArrayList<String> linhasArquivo,
			int start, int end) {
		linhasTreino.clear();
		linhasTeste.clear();
		for(int i = 0; i < linhasArquivo.size(); i++){
			if(start<=i && i <=end)
				linhasTeste.add(linhasArquivo.get(i));
			else
				linhasTreino.add(linhasArquivo.get(i));
		}
	}
	public static void main(String[] args) throws Exception {
		File folder = new File("/scratch/silviojr/testesLac");
		String resultDir = "/scratch/silviojr";
		int start = 1;
		int end = 2;
		
		int minM = 2;
		int maxM = 5;
				
		File[] listOfFiles = folder.listFiles();
		for (int fracao = start; fracao < end; fracao ++){
			for (int m = minM; m < maxM; m++){
				for (int i = 0; i < listOfFiles.length; i++) {
					System.out.println("Arquivo: " + listOfFiles[i] + " Num_Max_Regras: " + m);
					ArrayList<String> resultados = process(listOfFiles[i].getAbsolutePath(), 
														   fracao * 0.9, m, 
														   new double[]{});
					System.out.println("");
					String outFilename = String.format("%s/%s", 
													   resultDir, 
													   listOfFiles[i].getName()); 
					BufferedWriter bw = new BufferedWriter(new FileWriter(outFilename));
					//System.err.println(outFilename);
					
					for(int indice=0;indice<resultados.size();indice++){
						bw.append(resultados.get(indice));
						bw.newLine();
					}					
					bw.close();
				}
			}
		}
	}
}
