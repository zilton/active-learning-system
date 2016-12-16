package br.org.inweb.ctweb.lac.mbean;

public interface LacMBean {
	/** Carrega um novo treino no servidor */
	void load(int maxRuleSize, double minSupport, double minConfidence,
			boolean considerFeaturePosition, String trainName, String trainPath);
	/** Remove um treino do servidor */
	void remove(String trainName);
	/** Recupera a lista de treinos do servidor */
	String getTrainsName();
}
