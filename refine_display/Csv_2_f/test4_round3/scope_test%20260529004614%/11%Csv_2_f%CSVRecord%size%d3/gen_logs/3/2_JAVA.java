package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_11_3Test {

    @Test
    public void testSize_emptyArray() throws Exception {
        String[] values = new String[0];
        CSVRecord record = createCSVRecord(values, null, null, 0);
        Assertions.assertEquals(0, record.size());
    }

    @Test
    public void testSize_nonEmptyArray() throws Exception {
        String[] values = {"value1", "value2", "value3"};
        CSVRecord record = createCSVRecord(values, null, null, 0);
        Assertions.assertEquals(3, record.size());
    }

    @Test
    public void testSize_singleElementArray() throws Exception {
        String[] values = {"singleValue"};
        CSVRecord record = createCSVRecord(values, null, null, 0);
        Assertions.assertEquals(1, record.size());
    }

    private CSVRecord createCSVRecord(String[] values, Map<String, Integer> mapping, String comment, long recordNumber) throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, comment, recordNumber);
    }
}