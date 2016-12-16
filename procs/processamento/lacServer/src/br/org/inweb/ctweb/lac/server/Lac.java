package br.org.inweb.ctweb.lac.server;

import java.io.BufferedReader;
import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Set;
import java.util.TreeMap;

import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import weka.classifiers.rules.LACFeatureIndex;
import weka.classifiers.rules.LACInstance;
import weka.classifiers.rules.LACInstances;
import weka.classifiers.rules.LACRules;

public class Lac {
	private Logger log = LoggerFactory.getLogger(Lac.class);
	private HashMap<String, LACRules> treinosLac = new HashMap<String, LACRules>();
	private LACFeatureIndex featureIndex = null;
	private boolean ignoreNGrams;
	private String baseDir;
	
	public Lac(String baseDir, String path_treino_file, int max_rules_size, double min_support,
			double min_confidence, boolean considerFeaturePosition,
			boolean debug, LACFeatureIndex featureIndex, boolean ignoreNGrams) throws Exception {
		
		this.ignoreNGrams = ignoreNGrams;
		this.featureIndex = featureIndex;
		this.baseDir = baseDir;
		init(path_treino_file, max_rules_size, min_support, min_confidence,
				considerFeaturePosition, debug);
	}
	
	/**
	 * @param path_treino_file arquiv contendo informacoes sobre os treinos e contextos
	 * @param max_rules_size tamanho maximo das regras a serem geradas
	 * @param min_suport suporte minimo para um itemset ser considerado
	 * @param min_confidence confianca minima para uma regra de associação
	 * @param considerFeaturePosition considerar posicao da feature 
	 * @param debug opcao de debug (true or false)
	 */
	public Lac(String path_treino_file, int max_rules_size, double min_support,
			double min_confidence, boolean considerFeaturePosition,
			boolean debug) throws Exception {
		init(path_treino_file, max_rules_size, min_support, min_confidence,
				considerFeaturePosition, debug);
	}
	private void init(String path_treino_file, int max_rules_size, double min_support,
			double min_confidence, boolean considerFeaturePosition,
			boolean debug){
		BufferedReader reader = null;
		Map<String, String> contextosArqs = new TreeMap<String, String>();
		
		/*
		 * le o arquivo que contem a lista de treinos e contextos
		 * Formato: nome_contexto /caminho/para/arquivo_treino
		 */
		try {
			reader = new BufferedReader(new FileReader(path_treino_file));
		} catch (FileNotFoundException e) {
			throw new LacServerException("Arquivo com os treinos nao foi encontrado", e);
		}
		
		//mapea os diretorios para seus contextos, lendo cada linha do arquivo de treino
		mapearArquivoParaContexto(reader, contextosArqs);
		
		/*
		 * abre cada arquivo de treino e faz leitura de suas linhas, transforma-as em instancia de
		 * do lacRules e prepara uma instancia do lac.
		 * 
		 * Formato do arquivo: ID CLASS=NUM_CLASS w=word w=word_2 ... w=word_n
		 */
		for(Entry<String, String> contexto: contextosArqs.entrySet()) {
			String nomeContexto = (String) contexto.getKey();
			String arquivo = (String)contexto.getValue();
			
			construirClassificador(max_rules_size, min_support,
					min_confidence, considerFeaturePosition, debug,
					nomeContexto, arquivo);
		}
		log.info("treino construido");
	}
	/**
	 * Associa a cada contexto o seu arquivo de treino. Leitura feita do arquivo q contém a lista 
	 * de arquivos de treino
	 * @param reader
	 * @param contextoArquivo
	 */
	private void mapearArquivoParaContexto(BufferedReader reader,
										   Map<String, String> contextoArquivo) {
		String linha;
		try {
			while((linha = reader.readLine()) != null){
				String[] partes = linha.split("\\t");
				if(partes.length != 2) continue;
				//mapeia os diretorios (partes[1]) para cada contexto (partes[0])
				contextoArquivo.put(partes[0], partes[1]);
			}
			reader.close();
		} catch (IOException e) {
			throw new LacServerException(e);
		}
	}
	public void construirClassificador(int maxRuleSize, double minSupport,
			double minConfidence, boolean considerFeaturePosition,
			String trainName, String trainPath) {
		construirClassificador(maxRuleSize, minSupport, minConfidence,
				considerFeaturePosition, false, trainName, trainPath); 
	}
	/**
	 * 
	 * @param max_rules_size: tamanho maximo de uma regra
	 * @param min_support: suporte mínimo para itemset
	 * @param min_confidence: confiança mínima para regra
	 * @param considerFeaturePosition: considerar posição do atributo
	 * @param debug
	 * @param trainName
	 * @throws Exception
	 */
	public void construirClassificador(int maxRuleSize, double minSupport,
			double minConfidence, boolean considerFeaturePosition,
			boolean debug, String trainName, String trainPath) {
		synchronized(treinosLac){
			
			//cria dataset de treino
			LACInstances training = prepararInstanciasTreino(maxRuleSize,
					minSupport, minConfidence, considerFeaturePosition,
					debug, trainPath);
			
			try {
				LACRules lacRules = training.prepare(maxRuleSize, minSupport,
						minConfidence, considerFeaturePosition, debug);
				treinosLac.put(trainName, lacRules);
			} catch (Exception e) {
				throw new LacServerException(e);
			}
			log.info("Classificador para treino {} construído com sucesso.", trainName);
		}
	}

	/**
	 * Processa instâncias de treino
	 * @param max_rules_size: tamanho maximo das regras
	 * @param min_support: valor mínimo de suporte aceitável 
	 * @param min_confidence: confidência mínima aceitável para uma regtra
	 * @param considerFeaturePosition: conderar posição do atributo
	 * @param debug
	 * @param linhasTreino: linhas de treino, utilizadas para gerar cada LACInstance
	 * @return
	 */
	private LACInstances prepararInstanciasTreino(int maxRulesSize,
			double minSupport, double minConfidence,
			boolean considerFeaturePosition, boolean debug,
			String trainPath) {
		LACInstances training = new LACInstances(considerFeaturePosition, this.featureIndex);
		
		String linhaTreino;
		try {
			String fullPath = ""; 
			if (trainPath.substring(0) == "/"){
				fullPath = trainPath;
			} else {
				fullPath = this.baseDir + '/' + trainPath;
			}
			BufferedReader treinoReader = new BufferedReader(new FileReader(fullPath));
			while ((linhaTreino = treinoReader.readLine()) != null) {
				String[] partes = linhaTreino.split("\\s");
				if(partes.length > 2){
					LACInstance instance = training.createNewTrainingInstance();
					instance.setId(null); //No treino não precisa de ID. Diminui a memória alocada
					//Use new String() com substring para documentos grandes
					//Leia http://javarevisited.blogspot.sg/2011/10/how-substring-in-java-works.html
					instance.setClass(new String(partes[1].substring(6)));
					for(int j = 2; j < partes.length; j++){
						if(partes[j].length() > 3 && (!this.ignoreNGrams || partes[j].indexOf("_") < 0)){
							instance.addFeature(new String(partes[j].substring(2)));
						}
					}
				}

			}
			treinoReader.close();
		} catch (IOException e) {
			throw new LacServerException("Erro ao ler o arquivo " + trainPath + "(" + e.getMessage() + ")", e);
		}
		return training;
	}


	/**
	 * Classifica uma entrada de acordo com o seu contexto. Caso ocorra algum erro, retorna 
	 * {status: texto_erro}
	 * Caso contrário retorna:
	 * {stautus:ok, probabilidades:[], prediction: prediction, num_rules:num_regras, label:rotulo_inicial} 
	 * @param instancia - formato "id CLASS NUM w1=word1 w2=word2 ... wn=wordn
	 * @param nomeTreino - nome do treino do classificador ("dengue", "futebol" etc) a ser usado
	 * @param textoInstancia - texto da instancia a ser classificadaa ("ID CLASS=NUM w=word_1 w=word_2 w=word_n")
	 * @return resultado da classificacao no formato json
	 * @throws Exception 
	 */
	public String classificar(String nomeTreino, String textoInstancia) throws Exception{
		LACRules lac;
		synchronized(treinosLac){
			lac = treinosLac.get(nomeTreino);
		}
		JSONObject resultado = new JSONObject();
		
		if(lac == null){
			return resultado.put("status", "error: treino " + nomeTreino + " inexistente").toString();
		}
		
		LACInstance instance = lac.getTrainingInstances().createNewTrainingInstance(false);
		String partes[] = textoInstancia.trim().split("\\s");
		if(partes.length < 2){
			return resultado.put("status", "error: linha de texto mal formada").toString();
		}
		
		//monta instancia
		instance.setId(partes[0]);
		instance.setClass(new String(partes[1].substring(6)));
		for(int i=2;i<partes.length;i++){
			if (partes[i].length()>3){
				instance.addFeature(new String(partes[i].substring(2)));
			}
		}
		
		double[] probabilities = lac.calculateProbabilities(instance);
		
		int max_index = 0;
		TreeMap<String, Double> probs = new TreeMap<String, Double>();
		for(int i=0; i<probabilities.length;i++){
			if (probabilities[i] > probabilities[max_index]){
				max_index = i;
			}
			probs.put(lac.getTrainingInstances().getClassByIndex(i).getLabel(), probabilities[i]);
		}
		///instance.printRules();
		//System.out.println();
		//constroi objeto json
		resultado.put("status", "ok");
		resultado.put("id", partes[0]);
		resultado.put("probabilities", new JSONObject(probs));
		resultado.put("prediction", lac.getTrainingInstances().getClassByIndex(max_index));
		resultado.put("numRules", instance.getNumRules());
		resultado.put("label", new String(partes[1].substring(6)));
		return resultado.toString();
	}
	public Set<String> getTrainsName(){
		return this.treinosLac.keySet();
	}

	public void remove(String trainName) {
		synchronized (this.treinosLac) {
			this.treinosLac.remove(trainName);
			log.info("Treino {} removido", trainName);
		}
	}
}
