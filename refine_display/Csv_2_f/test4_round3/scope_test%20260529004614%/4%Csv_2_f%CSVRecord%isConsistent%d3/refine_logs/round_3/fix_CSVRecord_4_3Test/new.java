package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_4_3Test {

    @Test
    public void testisConsistent_mappingIsNull() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, null, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected record to be consistent when mapping is null.");
    }

    @Test
    public void testisConsistent_mappingSizeEqualsValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected record to be consistent when mapping size equals values length.");
    }

    @Test
    public void testisConsistent_mappingSizeNotEqualsValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertFalse(record.isConsistent(), "Expected record to be inconsistent when mapping size does not equal values length.");
    }

    @Test
    public void testisConsistent_emptyValuesAndNullMapping() throws Exception {
        CSVRecord record = new CSVRecord(new String[]{}, null, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected record to be consistent when values are empty and mapping is null.");
    }

    @Test
    public void testisConsistent_emptyValuesAndNonEmptyMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        
        CSVRecord record = new CSVRecord(new String[]{}, mapping, null, 1);
        Assertions.assertFalse(record.isConsistent(), "Expected record to be inconsistent when values are empty and mapping is non-empty.");
    }

    @Test
    public void testisConsistent_singleValueWithMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        
        CSVRecord record = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected record to be consistent when there is a single value with mapping.");
    }

    @Test
    public void testisConsistent_multipleValuesWithMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertTrue(record.isConsistent(), "Expected record to be consistent when multiple values match the mapping.");
    }

    @Test
    public void testisConsistent_exceedsMapping() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("column1", 0);
        mapping.put("column2", 1);
        mapping.put("column3", 2);
        
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertFalse(record.isConsistent(), "Expected record to be inconsistent when values exceed mapping.");
    }
}