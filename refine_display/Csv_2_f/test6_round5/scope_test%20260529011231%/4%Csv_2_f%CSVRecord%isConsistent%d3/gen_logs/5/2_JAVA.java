package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

class CSVRecord_4_5Test {

    @Test
    void testIsConsistent_mappingIsNull() {
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, null, null, 1);
        Assertions.assertTrue(record.isConsistent());
    }

    @Test
    void testIsConsistent_mappingSizeEqualsValuesLength() {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);
        mapping.put("key2", 1);
        
        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertTrue(record.isConsistent());
    }

    @Test
    void testIsConsistent_mappingSizeNotEqualsValuesLength() {
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("key1", 0);

        CSVRecord record = new CSVRecord(new String[]{"value1", "value2"}, mapping, null, 1);
        Assertions.assertFalse(record.isConsistent());
    }
}