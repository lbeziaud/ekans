def sample_targets(df, n_targets):
    return df.sample(n=n_targets, replace=False).index