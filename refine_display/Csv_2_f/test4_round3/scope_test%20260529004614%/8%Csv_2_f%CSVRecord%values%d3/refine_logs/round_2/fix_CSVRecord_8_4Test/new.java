package org.apache.commons.csv;

import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_8_4Test {

    @Test
    public void testvalues_nonEmptyArray() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        
        String[] result = (String[]) method.invoke(record);
        Assertions.assertNotNull(result);
        Assertions.assertEquals(values.length, result.length);
        for (int i = 0; i < values.length; i++) {
            Assertions.assertEquals(values[i], result[i]);
        }
    }

    @Test
    public void testvalues_emptyArray() throws Exception {
        String[] values = {};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        
        String[] result = (String[]) method.invoke(record);
        Assertions.assertNotNull(result);
        Assertions.assertEquals(0, result.length);
    }

    @Test
    public void testvalues_nullArray() throws Exception {
        String[] values = null;
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(values, mapping, null, 1);
        
        Method method = CSVRecord.class.getDeclaredMethod("values");
        method.setAccessible(true);
        
        String[] result = (String[]) method.invoke(record);
        Assertions.assertNotNull(result);
        Assertions.assertArrayEquals(new String[0], result);
    }
}