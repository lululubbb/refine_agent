package org.apache.commons.csv;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_10_3Test {

    @Test
    public void testGetRecordNumber_normalCase() throws Exception {
        // Arrange
        String[] values = {"value1", "value2"};
        Map<String, Integer> mapping = new HashMap<>();
        String comment = "Test comment";
        long expectedRecordNumber = 42L;

        CSVRecord csvRecord = createCSVRecord(values, mapping, comment, expectedRecordNumber);

        // Act
        long actualRecordNumber = csvRecord.getRecordNumber();

        // Assert
        Assertions.assertEquals(expectedRecordNumber, actualRecordNumber);
    }

    private CSVRecord createCSVRecord(String[] values, Map<String, Integer> mapping, String comment, long recordNumber) 
            throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, comment, recordNumber);
    }
}