package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

class CSVRecord_4_2Test {

    @Test
    void testisConsistent_mappingIsNull() throws Exception {
        CSVRecord csvRecord = new CSVRecord(new String[]{"value1", "value2"}, null, null, 1);
        Assertions.assertTrue(csvRecord.isConsistent());
    }

    @Test
    void testisConsistent_mappingSizeEqualsValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        
        CSVRecord csvRecord = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertTrue(csvRecord.isConsistent());
    }

    @Test
    void testisConsistent_mappingSizeNotEqualsValuesLength() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        
        CSVRecord csvRecord = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertFalse(csvRecord.isConsistent());
    }

    @Test
    void testisConsistent_emptyValuesArray() throws Exception {
        Map<String, Integer> mapping = new HashMap<>();
        
        CSVRecord csvRecord = new CSVRecord(new String[]{}, mapping, null, 1);
        Assertions.assertFalse(csvRecord.isConsistent());
    }

    @Test
    void testisConsistent_emptyMapping() throws Exception {
        Map<String, Integer> mapping = Collections.emptyMap();
        
        CSVRecord csvRecord = new CSVRecord(new String[]{"value1"}, mapping, null, 1);
        Assertions.assertFalse(csvRecord.isConsistent());
    }
}