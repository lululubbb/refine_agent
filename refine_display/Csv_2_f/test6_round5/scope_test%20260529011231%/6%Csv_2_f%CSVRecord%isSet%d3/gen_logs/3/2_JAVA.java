package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.util.HashMap;
import java.util.Map;

public class CSVRecord_6_3Test {
    private CSVRecord csvRecord;
    private Map<String, Integer> mapping;

    @BeforeEach
    public void setUp() {
        mapping = new HashMap<>();
    }

    @Test
    public void testisSet_normalCase() throws Exception {
        String[] values = {"value1", "value2"};
        mapping.put("key1", 0);
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        boolean result = csvRecord.isSet("key1");
        Assertions.assertTrue(result);
    }

    @Test
    public void testisSet_keyNotMapped() throws Exception {
        String[] values = {"value1", "value2"};
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        boolean result = csvRecord.isSet("key2");
        Assertions.assertFalse(result);
    }

    @Test
    public void testisSet_indexOutOfBounds() throws Exception {
        String[] values = {"value1"};
        mapping.put("key1", 1);
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        boolean result = csvRecord.isSet("key1");
        Assertions.assertFalse(result);
    }

    @Test
    public void testisSet_emptyValuesArray() throws Exception {
        String[] values = {};
        mapping.put("key1", 0);
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        boolean result = csvRecord.isSet("key1");
        Assertions.assertFalse(result);
    }

    @Test
    public void testisSet_mappedButNotSet() throws Exception {
        String[] values = {"value1"};
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        csvRecord = new CSVRecord(values, mapping, null, 1);
        
        boolean result1 = csvRecord.isSet("key1");
        boolean result2 = csvRecord.isSet("key2");
        Assertions.assertTrue(result1);
        Assertions.assertFalse(result2);
    }
}